"""Reviewed academic text bound to immutable evidence, without private reports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any
import zipfile

from ecoscan.config import AppConfig

FROZEN_SOURCE_SHA = "89622ec714b815c216a9215ab9ba69999b39c6b8"
COMPANION_FILES = (
    "indice_evidencias.md",
    "roteiro_seminario.md",
    "ficha_aps_preenchimento_privado.md",
    "fontes_verificadas.json",
    "evidencias.json",
)


def checked_evidence(config: AppConfig) -> dict[str, Any]:
    """Refuse stale evidence instead of relabelling reviewed text with a new SHA."""
    root = config.project_root
    evidence = json.loads((root / "docs/aps/evidencias.json").read_text(encoding="utf-8"))
    if (
        evidence["source_sha"] != FROZEN_SOURCE_SHA
        or evidence["academic_submission_ready"] is not False
        or evidence["independent_test"] is not False
    ):
        raise ValueError("Academic evidence needs a new review for this source/acceptance state")
    for name, record in evidence["source_files"].items():
        path = root / name
        if (
            Path(name).is_absolute()
            or ".." in Path(name).parts
            or "\\" in name
            or not path.resolve().is_relative_to(root.resolve())
            or path.is_symlink()
            or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]
        ):
            raise ValueError("Source evidence changed; review the frozen academic base")
    for row in evidence["requirements"]:
        for key in ("code", "test_or_reference"):
            location = row[key]
            if location["path"] not in evidence["source_files"]:
                raise ValueError("Unbound academic reference")
            expected_url = (
                f"https://github.com/Gabrielhamad/ecoscan/blob/{FROZEN_SOURCE_SHA}/"
                f"{location['path']}#L{location['line']}"
            )
            if location["url"] != expected_url:
                raise ValueError("Academic link must use the frozen SHA and line")
            lines = (root / location["path"]).read_text(encoding="utf-8").splitlines()
            if location["anchor"] and location["anchor"] not in lines[location["line"] - 1]:
                raise ValueError("Academic line reference changed")
    return evidence


def _percentage(value: float) -> str:
    return f"{100 * value:.2f}%".replace(".", ",")


def measured_model_tables(config: AppConfig) -> str:
    root = config.project_root
    historical = json.loads(
        (root / "docs/model_evaluation/semantic_v1_historical.json").read_text()
    )
    external = json.loads(
        (root / "docs/model_evaluation/trashnet_priority_diagnostic.json").read_text()
    )
    if historical["independent_test"] is not False or external["independent_test"] is not False:
        raise ValueError("Independent evidence requires a new academic review")
    columns = []
    for data in (historical, external["evaluation"]):
        top, acceptance = data["top1"], data["acceptance"]
        total, accepted = top["total"], acceptance["accepted"]
        columns.append(
            {
                "N": str(total),
                "Top-1 correto": str(round(top["accuracy"] * total)),
                "Acurácia top-1": _percentage(top["accuracy"]),
                "Precisão macro": _percentage(top["macro_precision"]),
                "Recall macro": _percentage(top["macro_recall"]),
                "F1 macro": f"{top['macro_f1']:.4f}",
                "Aceitos pelo artefato": str(accepted),
                "Erros entre aceitos": str(acceptance["wrong"]),
                "Rejeitados": str(acceptance["rejected"]),
                "Precisão entre aceitos": _percentage(acceptance["correct"] / accepted),
                "Cobertura do artefato": _percentage(accepted / total),
                "Erro entre aceitos": _percentage(acceptance["wrong"] / accepted),
                "Taxa de rejeição": _percentage(acceptance["rejected"] / total),
            }
        )
    lines = ["| Métrica | Histórico reutilizado | TrashNet diagnóstico |", "| --- | ---: | ---: |"]
    for key in columns[0]:
        lines.append(f"| {key} | {columns[0][key]} | {columns[1][key]} |")
    lines += [
        "",
        "Histórico, por classe, antes da confirmação humana:",
        "",
        "| Classe | N | Precisão top-1 | Recall top-1 | F1 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for label, row in historical["top1"]["by_class"].items():
        lines.append(
            f"| {label} | {row['support']} | {_percentage(row['precision'])} | {_percentage(row['recall'])} | {row['f1']:.4f} |"
        )
    top = historical["top1"]
    classes = top["classes"]
    lines += [
        "",
        "Matriz histórica: linhas = rótulo de referência; colunas = top-1 previsto.",
        "B=battery; E=electronic; G=glass; M=metal; P=paper_cardboard; L=plastic.",
        "",
        "| Real | B | E | G | M | P | L |",
        "| --- | " + " | ".join("---:" for _ in classes) + " |",
    ]
    for label, values in zip("BEGMPL", top["confusion_matrix"], strict=True):
        lines.append("| " + label + " | " + " | ".join(map(str, values)) + " |")
    return "\n".join(lines)


def measured_processing_tables(config: AppConfig) -> str:
    folder = config.project_root / "docs/preparation_evidence"
    lines = [
        "| Registro histórico | Condição | N | ΔSSIM médio | Casos com queda de SSIM |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for name in ("default", "sigma8"):
        data = json.loads((folder / (name + ".json")).read_text())
        for condition, row in data["summary"].items():
            lines.append(
                f"| {name}.json | {condition} | {row['count']} | {row['mean_delta_ssim']:+.6f} | {row['worsened']} |"
            )
    return "\n".join(lines)


def build_academic_report(config: AppConfig) -> str:
    """Do not count local photos or ingest ambient reports as scientific evidence."""
    checked_evidence(config)
    text = (config.project_root / "docs/aps/relatorio_tecnico.md").read_text(encoding="utf-8")
    for name, body in [
        ("MODEL", measured_model_tables(config)),
        ("PDI", measured_processing_tables(config)),
    ]:
        pattern = rf"<!-- {name}:BEGIN -->.*?<!-- {name}:END -->"
        text, count = re.subn(
            pattern, f"<!-- {name}:BEGIN -->\n{body}\n<!-- {name}:END -->", text, flags=re.S
        )
        if count != 1:
            raise ValueError("Missing or duplicate measured result block")
    return text


def write_academic_report(config: AppConfig, output_path: str | Path | None = None) -> Path:
    path = (
        Path(output_path).resolve()
        if output_path
        else config.directories["reports"] / "aps_report/relatorio_aps.md"
    )
    report = build_academic_report(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    for name in COMPANION_FILES:
        source, target = config.project_root / "docs/aps" / name, path.parent / name
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)
    return path


def write_code_appendix(config: AppConfig, output: Path) -> Path:
    """Export public code from the documented Git commit; never from local data."""
    checked_evidence(config)
    root = config.project_root
    records = subprocess.run(
        ["git", "ls-tree", "-r", "-z", FROZEN_SOURCE_SHA],
        cwd=root,
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout.split(b"\0")
    output.parent.mkdir(parents=True, exist_ok=True)
    hashes = {}
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for record in records:
            if not record:
                continue
            metadata, raw_name = record.split(b"\t", 1)
            name = raw_name.decode()
            relative = Path(name)
            if not (
                (
                    relative.parts[0] in {"src", "scripts", "tests", "migrations"}
                    and relative.suffix in {".py", ".sql", ".css", ".html"}
                )
                or name
                in {
                    "streamlit_app.py",
                    "pyproject.toml",
                    "requirements.txt",
                    "models/semantic-v1/LICENSE-CLIP",
                }
            ):
                continue
            if metadata.split()[0] not in {b"100644", b"100755"}:
                raise ValueError("Links are not code appendix inputs")
            data = subprocess.run(
                ["git", "show", FROZEN_SOURCE_SHA + ":" + name],
                cwd=root,
                check=True,
                capture_output=True,
                timeout=30,
            ).stdout
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
            hashes[name] = hashlib.sha256(data).hexdigest()
        info = zipfile.ZipInfo("APENDICE_MANIFEST.json", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(
            info,
            json.dumps(
                {
                    "source_sha": FROZEN_SOURCE_SHA,
                    "purpose": "Code audit appendix, not an executable release",
                    "files": hashes,
                },
                indent=2,
            ),
        )
    return output
