"""Build review-only execution archives from a committed snapshot and an explicit lock."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import platform
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import tomllib
import zipfile
from typing import Any

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

REPOSITORY = "Gabrielhamad/ecoscan"
CONFIG_FILES = {
    "settings.json",
    "education.json",
    "disposal_guidance.json",
    "disposal_targets.json",
    "environmental_impacts.json",
    "photo_requirements.json",
    "collection_points.json",
    "campaigns.json",
}
MODEL_FILES = {
    "semantic.json",
    "head.npz",
    "LICENSE-CLIP",
    "README.md",
    "encoder_00.part",
    "encoder_01.part",
    "encoder_02.part",
    "encoder_03.part",
}
DOC_FILES = {
    "docs/modelo_reconhecimento.md",
    "docs/pratica_processamento_imagens.md",
    "docs/arquitetura_atual.md",
}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=True, timeout=30
    ).stdout


def source_sha(root: Path, ref: str) -> str:
    sha = git(root, "rev-parse", "--verify", ref + "^{commit}").decode().strip()
    if not re.fullmatch("[a-f0-9]{40}", sha):
        raise ValueError("A full committed Git SHA is required")
    return sha


def allowed_source(name: str) -> bool:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        return False
    return (
        name in {"streamlit_app.py", "pyproject.toml", "README.md", "requirements.txt"}
        or name in DOC_FILES
        or (path.parent.as_posix() == "config" and path.name in CONFIG_FILES)
        or (name.startswith("src/ecoscan/") and path.suffix in {".py", ".css", ".html"})
        or (path.parent.as_posix() == "models/semantic-v1" and path.name in MODEL_FILES)
    )


def copy_snapshot(root: Path, sha: str, stage: Path) -> dict[str, str]:
    origins = {}
    for record in git(root, "ls-tree", "-r", "-z", sha).split(b"\0"):
        if not record:
            continue
        mode_type_oid, raw_name = record.split(b"\t", 1)
        name = raw_name.decode("utf-8")
        if not allowed_source(name):
            continue
        mode, kind, _ = mode_type_oid.decode().split()
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError("Links/submodules are not execution-package inputs")
        relative = {
            "README.md": "docs/SOURCE_README.md",
            "requirements.txt": "requirements.source.txt",
        }.get(name, name)
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as stream:
            subprocess.run(
                ["git", "show", sha + ":" + name],
                cwd=root,
                stdout=stream,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=30,
            )
        origins[relative] = "git:" + sha + ":" + name
    return origins


def read_runtime_lock(data: bytes, project: dict[str, Any]) -> dict[str, str]:
    pins = {}
    for line in data.decode("utf-8").replace("\\\n", " ").splitlines():
        line = line.strip()
        if not line:
            continue
        tokens = line.split()
        if len(tokens) < 2 or any(
            not re.fullmatch(r"--hash=sha256:[0-9a-f]{64}", token) for token in tokens[1:]
        ):
            raise ValueError("Only exact pins and SHA-256 hashes are allowed in a delivery lock")
        requirement = Requirement(tokens[0])
        specs = list(requirement.specifier)
        if (
            len(specs) != 1
            or specs[0].operator != "=="
            or "*" in specs[0].version
            or requirement.url
            or requirement.marker
            or requirement.extras
        ):
            raise ValueError("Use an exact, hashed lock for the tested Python/platform")
        name = canonicalize_name(requirement.name)
        if name in pins or name in {
            "torch",
            "tensorflow",
            "playwright",
            "pytest",
            "ruff",
            "pip-audit",
        }:
            raise ValueError("Duplicate or non-runtime dependency")
        pins[name] = specs[0].version
    for requirement in map(Requirement, project["project"]["dependencies"]):
        name = canonicalize_name(requirement.name)
        if name not in pins or pins[name] not in requirement.specifier:
            raise ValueError("Lock does not satisfy the committed project")
    return pins


def ci_evidence(path: Path | None, sha: str) -> dict[str, Any]:
    if path is None:
        return {"conclusion": "not_provided", "source_sha": sha, "run_url": None}
    data = json.loads(path.read_text())
    if (
        set(data) != {"source_sha", "conclusion", "run_url", "kind", "release_acceptance"}
        or data["source_sha"] != sha
        or data["conclusion"] not in {"success", "failure", "cancelled"}
        or data["kind"] != "github_api_observation"
        or data["release_acceptance"] != "not_approved"
        or not re.fullmatch(
            r"https://github\.com/Gabrielhamad/ecoscan/actions/runs/\d+", data["run_url"]
        )
    ):
        raise ValueError(
            "Use only CI metadata for the source SHA; no log, URL query or approval shortcut"
        )
    return data


def validate_model(stage: Path) -> dict[str, Any]:
    from ecoscan.classification.semantic_onnx import file_digest, resolve_encoder
    from ecoscan.config import load_config
    from ecoscan.image_processing.contracts import processing_contract

    folder = stage / "models/semantic-v1"
    config = load_config(stage / "config/settings.json")
    if (
        config.model["artifact_path"] != "models/semantic-v1/semantic.json"
        or config.model.get("engine") != "semantic_onnx_assisted"
        or config.model.get("confirmation_required", True) is not True
    ):
        raise ValueError("Unexpected configured model")
    metadata = json.loads((folder / "semantic.json").read_text())
    if metadata["processing"] != processing_contract(config) or set(metadata["classes"]) != set(
        config.classes
    ) | {"unknown"}:
        raise ValueError("Model/processing scope mismatch")
    if file_digest(folder / "head.npz") != metadata["head_sha256"]:
        raise ValueError("Head checksum mismatch")
    license_text = (folder / "LICENSE-CLIP").read_text()
    if "MIT License" not in license_text or "OpenAI" not in license_text:
        raise ValueError("The encoder license must accompany redistribution")
    # The existing resolver validates each part and the assembled hash.
    encoder = resolve_encoder(folder, metadata)
    combined = file_digest(encoder)
    encoder.unlink()  # derivative cache is regenerated on the presentation computer
    return {
        "artifact": "models/semantic-v1/semantic.json",
        "metadata_sha256": file_digest(folder / "semantic.json"),
        "head_sha256": metadata["head_sha256"],
        "encoder_sha256": combined,
        "processing_sha256": metadata["processing"]["sha256"],
        "parts": metadata["parts"],
        "encoder_license": "MIT; models/semantic-v1/LICENSE-CLIP",
        "head_origin": "project-generated parameters; no training seed or photos distributed",
        "threshold": metadata["threshold"],
        "confirmation_required": True,
    }


def safe_local_config(stage: Path) -> None:
    path = stage / "config/settings.json"
    settings = json.loads(path.read_text())
    for directory in settings["directories"].values():
        value = PurePosixPath(directory)
        if value.is_absolute() or ".." in value.parts or "\\" in directory or ":" in directory:
            raise ValueError("Package configuration must use local relative directories")
    # Only delivery-profile flags change; the processing contract stays intact.
    settings["model"]["remote_models_enabled"] = False
    settings["history"]["enabled"] = False
    path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def model_results(root: Path, sha: str, model: dict[str, Any]) -> dict[str, Any]:
    path = "docs/model_evaluation/semantic_v1_historical.json"
    try:
        raw = git(root, "show", sha + ":" + path)
    except subprocess.CalledProcessError:
        return {"status": "not_available", "independent_test": False}
    data = json.loads(raw)
    expected = {
        "semantic_sha256": model["metadata_sha256"],
        "head_sha256": model["head_sha256"],
        "encoder_sha256": model["encoder_sha256"],
        "processing_sha256": model["processing_sha256"],
    }
    if (
        any(data["artifacts"].get(key) != value for key, value in expected.items())
        or data["independent_test"] is not False
    ):
        raise ValueError("Historical results do not match this artifact or need independent review")
    metrics = {
        name: data["top1"][name]
        for name in ("accuracy", "macro_precision", "macro_recall", "macro_f1", "total")
    }
    if any(
        not isinstance(value, (int, float)) or not math.isfinite(value)
        for value in metrics.values()
    ):
        raise ValueError("Invalid result values")
    return {
        "status": "historical_reused_features_only",
        "independent_test": False,
        "source": path,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "top1": metrics,
        "limitation": "Historical features reused; not field accuracy or an independent promotion gate",
    }


def write_color_panels(stage: Path) -> list[str]:
    """Draw simple UI color keys; never copy source rasters or create evidence photos."""
    from PIL import Image, ImageDraw

    targets_path = stage / "config/disposal_targets.json"
    targets = json.loads(targets_path.read_text()) if targets_path.exists() else {}
    paths = []
    for target in targets.values():
        name, color = target["asset_path"], target["bin_color_hex"]
        if not re.fullmatch(r"assets/disposal_targets/[a-z_]+\.png", name) or not re.fullmatch(
            r"#[a-fA-F0-9]{6}", color
        ):
            raise ValueError("Invalid color panel configuration")
        path = stage / name
        path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (160, 160), "#f4f6f5")
        draw = ImageDraw.Draw(image)
        draw.rectangle((30, 30, 130, 130), fill=color, outline="#26352f", width=3)
        image.save(path, format="PNG")
        paths.append(name)
    return sorted(paths)


def copy_authorized_photos(
    stage: Path, root: Path | None, manifest: Path | None
) -> list[dict[str, Any]]:
    if root is None and manifest is None:
        return []
    if root is None or manifest is None:
        raise ValueError("Both photo root and reviewed manifest are required")
    from PIL import Image
    from ecoscan.image_processing.validation import validate_image_file

    rows = json.loads(manifest.read_text())
    if set(rows) != {"images"}:
        raise ValueError("Only reviewed image metadata is accepted")
    result, hashes = [], set()
    for index, row in enumerate(rows["images"], start=1):
        if (
            set(row)
            != {
                "path",
                "sha256",
                "source_kind",
                "license",
                "attribution",
                "distribution_allowed",
                "no_personal_data",
            }
            or row["source_kind"] not in {"real_authorized_photo", "technical_fixture"}
            or row["license"] not in {"CC0-1.0", "CC-BY-4.0"}
            or row["distribution_allowed"] is not True
            or row["no_personal_data"] is not True
            or not re.fullmatch(r"[\w .-]{1,120}", row["attribution"])
        ):
            raise ValueError(
                "Redistribution/metadata review is required; no private notes or identity links"
            )
        relative = PurePosixPath(row["path"])
        path = root / row["path"]
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or "\\" in row["path"]
            or path.is_symlink()
            or not path.resolve().is_relative_to(root.resolve())
            or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}
        ):
            raise ValueError("Image path outside the reviewed root")
        if digest(path) != row["sha256"] or row["sha256"] in hashes:
            raise ValueError("Image changed or duplicated")
        info = validate_image_file(
            path, allowed_extensions={".jpg", ".jpeg", ".png"}, min_size=(32, 32)
        )
        if info.format != ("PNG" if path.suffix.lower() == ".png" else "JPEG"):
            raise ValueError("Image format differs from its extension")
        with Image.open(path) as image:
            if any(tag != 274 for tag in image.getexif()) or getattr(image, "text", {}):
                raise ValueError(
                    "Remove private EXIF/text metadata before authorization; no silent image rewrite"
                )
        hashes.add(row["sha256"])
        destination = f"examples/photo_{index:03}" + path.suffix.lower()
        (stage / "examples").mkdir(exist_ok=True)
        shutil.copyfile(path, stage / destination)
        result.append(
            {key: row[key] for key in ("sha256", "source_kind", "license", "attribution")}
            | {"path": destination}
        )
    return result


def write_execution_package(
    root: Path,
    output: Path,
    *,
    ref: str,
    runtime_lock: Path,
    builder_root: Path,
    lock_ref: str | None = None,
    ci_report: Path | None = None,
    photos_root: Path | None = None,
    photos_manifest: Path | None = None,
) -> dict[str, Path]:
    """Build a review artifact; this function cannot approve a release or create a tag."""
    if output.exists():
        raise ValueError("Use a new output directory")
    sha = source_sha(root, ref)
    lock_bytes = runtime_lock.read_bytes()
    if (
        lock_ref
        and git(root, "show", source_sha(root, lock_ref) + ":requirements.lock") != lock_bytes
    ):
        raise ValueError("Lock differs from its declared Git provenance")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ecoscan-delivery-", dir=output.parent) as temporary:
        stage = Path(temporary) / "ecoscan"
        stage.mkdir()
        origins = copy_snapshot(root, sha, stage)
        pins = read_runtime_lock(lock_bytes, tomllib.loads((stage / "pyproject.toml").read_text()))
        model = validate_model(stage)
        safe_local_config(stage)
        origins["config/settings.json"] += (
            "; generated local profile: remote models/history disabled"
        )
        panels = write_color_panels(stage)
        for name in panels:
            origins[name] = (
                "generated geometric color key; no source raster copied; not a photograph"
            )
        for name in (
            "scripts/run_delivery_demo.py",
            "run_ecoscan_rede.bat",
            "run_ecoscan_rede.ps1",
            "config/delivery_demo.toml",
        ):
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(builder_root / name, path)
            origins[name] = "builder-generated helper; file hash below"
        generated = {
            "requirements.delivery.lock": lock_bytes,
            "requirements.txt": b"-r requirements.delivery.lock\n",
            ".streamlit/config.toml": b'[server]\nheadless=true\nmaxUploadSize=15\n[browser]\ngatherUsageStats=false\n[secrets]\nfiles=["config/delivery_demo.toml"]\n',
            "config/servicos.example.toml": b"# Optional services require separate authorized setup; never place credentials in this review package.\n[persistence]\n# url and service_key must stay outside the distributed package.\n",
            "examples/README.md": b"No real images are provided by default. Include only reviewed, redistribution-authorized photos with the explicit manifest option. Technical fixtures never prove field accuracy.\n",
            "README.md": execution_readme(sha).encode("utf-8"),
            "README_EXECUCAO.md": execution_readme(sha).encode("utf-8"),
        }
        for name, data in generated.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            origins[name] = "generated delivery profile"
        photos = copy_authorized_photos(stage, photos_root, photos_manifest)
        for photo in photos:
            origins[photo["path"]] = (
                "explicitly redistribution-authorized input; anonymized filename"
            )
        builder_sha = source_sha(builder_root, "HEAD")
        dirty = bool(git(builder_root, "status", "--porcelain", "--untracked-files=normal").strip())
        manifest_data = {
            "schema_version": 1,
            "stage": "review_candidate_not_release",
            "release_ready": False,
            "source_repository": REPOSITORY,
            "source_sha": sha,
            "builder_sha": None if dirty else builder_sha,
            "builder_workspace_dirty": dirty,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "python_required": "3.12",
            "builder_python": platform.python_version(),
            "lock_target_platform": platform.system() + "/" + platform.machine(),
            "dependencies": pins,
            "runtime_lock_sha256": hashlib.sha256(lock_bytes).hexdigest(),
            "lock_source_ref": lock_ref,
            "execution": {
                "method": "Streamlit/Python, no native exe",
                "command": "python scripts/run_delivery_demo.py serve",
                "bind_default": "127.0.0.1",
                "network_credentials": "disabled in local demo profile",
            },
            "model": model,
            "model_results": model_results(root, sha, model),
            "ci": ci_evidence(ci_report, sha),
            "ui_color_panels": panels,
            "photos": photos,
            "offline_real_photo_copy": "manual_pending"
            if not any(p["source_kind"] == "real_authorized_photo" for p in photos)
            else "requires_device_smoke",
            "external_acceptance": {
                key: "manual_pending" for key in ("QA-09", "QA-18", "QA-19", "QA-20", "QA-21")
            },
            "limitations": [
                "CI is not SHA acceptance or an independent model evaluation",
                "Presentation PC, Windows/PowerShell and real phones require manual smoke",
                "Initial dependency installation needs Internet; no wheelhouse is bundled",
                "Maps, CEP and optional Supabase require network and separate authorization",
                "Unlicensed raster assets, accounts, training seeds, datasets, backups and Secrets omitted",
                "UI color keys are generated geometric panels, not photos or field evidence",
                "Known main privacy finding must be reviewed; open PRs are not deployed improvements",
            ],
        }
        manifest_data["files"] = [
            {
                "path": path.relative_to(stage).as_posix(),
                "sha256": digest(path),
                "origin": origins[path.relative_to(stage).as_posix()],
            }
            for path in sorted(stage.rglob("*"))
            if path.is_file()
        ]
        (stage / "delivery_manifest.json").write_text(
            json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        destination = Path(temporary) / "result"
        destination.mkdir()
        archive_path = destination / f"ecoscan-review-{sha[:12]}.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    archive.write(path, "ecoscan/" + path.relative_to(stage).as_posix())
        shutil.copyfile(stage / "delivery_manifest.json", destination / "delivery_manifest.json")
        checksum = digest(archive_path)
        (destination / "SHA256SUMS").write_text(checksum + "  " + archive_path.name + "\n")
        destination.rename(output)
    return {
        "archive": output / archive_path.name,
        "manifest": output / "delivery_manifest.json",
        "checksums": output / "SHA256SUMS",
    }


def execution_readme(sha: str) -> str:
    return f"""# EcoScan — execução local APS (pacote de revisão)

Fonte do programa: `{sha}`. Não é release aprovada, não é instalador `.exe`.
O helper e o perfil local são identificados por hash no delivery_manifest.json.

1. Instale Python **3.12** e extraia o ZIP em uma pasta gravável.
2. Crie o ambiente: `python -m venv .venv` (Windows: `py -3.12 -m venv .venv`).
3. Ative: `source .venv/bin/activate` ou `.venv\\Scripts\\activate.bat`.
4. Instale: `python -m pip install --require-hashes --only-binary=:all: -r requirements.txt`.
5. Verifique: `python scripts/run_delivery_demo.py verify` e `python -m pip check`.
6. Abra: `python scripts/run_delivery_demo.py serve` ou `run_ecoscan_rede.bat`.
7. Acesse http://localhost:8501. Ctrl+C encerra apenas esta instância.

O lock é da plataforma testada; Windows e o PC de apresentação continuam sujeitos
à instalação limpa e smoke reais. Não force uma versão divergente para obter verde.
Use `--port 8510` se necessário; `--lan` somente para uma rede local autorizada.
O launcher não encerra processos alheios nem inicia o backend Live separado.

Sem Secrets, contas ou banco: o perfil local não carrega credenciais globais.
Não use fotos privadas. Exemplos reais só entram mediante licença/consentimento
explícitos e revisão de metadados; examples/ informa a pendência quando ausentes.
Após instalar dependências, o núcleo e modelo são locais. Mapas/CEP precisam de Internet.

O modelo é assistido: confirme o material para consultar a orientação. Os resultados
no manifesto são históricos reutilizados, não acurácia de campo independente.
Arquivos raster sem licença comprovada foram omitidos. Painéis geométricos de cor
são gerados pelo empacotador apenas para a UI; não são fotos nem evidência PDI.
A licença MIT do encoder CLIP acompanha o modelo. Não foi concedida nova licença ao projeto.

Confira SHA256SUMS antes de extrair e delivery_manifest.json para a lista de hashes.
O verifier comprova integridade contra o manifesto, não assinatura/autenticidade do ZIP.
Compare o checksum recebido por um canal confiável do grupo.
Rollback: Ctrl+C e volte ao pacote anterior identificado por SHA; não apague banco,
Secrets, imagens originais ou evidências para restaurar o app. Para tag/release,
exigir CI e aceite do SHA, dados reais/autorizados e smoke no PC de apresentação.
"""


def verify_execution_archive(path: Path) -> dict[str, Any]:
    """Inspect bytes without extracting; unknown files/links/duplicates are rejected."""
    generated = {
        "README.md",
        "README_EXECUCAO.md",
        "requirements.txt",
        "requirements.source.txt",
        "requirements.delivery.lock",
        ".streamlit/config.toml",
        "config/servicos.example.toml",
        "config/delivery_demo.toml",
        "docs/SOURCE_README.md",
        "scripts/run_delivery_demo.py",
        "run_ecoscan_rede.bat",
        "run_ecoscan_rede.ps1",
        "examples/README.md",
    }
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if (
            len(names) != len(set(names))
            or len(entries) > 1000
            or sum(row.file_size for row in entries) > 1024**3
        ):
            raise ValueError("Duplicate entries or oversized execution archive")
        manifest = json.loads(archive.read("ecoscan/delivery_manifest.json"))
        if (
            manifest["stage"] != "review_candidate_not_release"
            or manifest["release_ready"] is not False
        ):
            raise ValueError("This tool produces review packages only; release gate is separate")
        expected = {"ecoscan/delivery_manifest.json"} | {
            "ecoscan/" + row["path"] for row in manifest["files"]
        }
        if set(names) != expected:
            raise ValueError("Archive has missing or unexpected files")
        for entry in entries:
            relative = PurePosixPath(entry.filename)
            if (
                relative.parts[0] != "ecoscan"
                or ".." in relative.parts
                or "\\" in entry.filename
                or ((entry.external_attr >> 16) & 0o170000) == 0o120000
            ):
                raise ValueError("Unsafe archive path/link")
        for row in manifest["files"]:
            name = row["path"]
            if not (
                allowed_source(name)
                or name in generated
                or name in manifest["ui_color_panels"]
                or re.fullmatch(r"examples/photo_\d{3}\.(png|jpg|jpeg)", name)
            ):
                raise ValueError("File outside the execution allowlist")
            if name in manifest["ui_color_panels"] and not re.fullmatch(
                r"assets/disposal_targets/[a-z_]+\.png", name
            ):
                raise ValueError("Invalid UI panel path")
            with archive.open("ecoscan/" + name) as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != row["sha256"]:
                    raise ValueError("Archive checksum mismatch")
        return {
            "stage": manifest["stage"],
            "source_sha": manifest["source_sha"],
            "files_verified": len(manifest["files"]),
            "model": manifest["model"],
            "offline_real_photo_copy": manifest["offline_real_photo_copy"],
        }
