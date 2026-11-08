"""Tiny synthetic artifacts prove packaging rules; actual ONNX smoke is separate."""

import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from PIL import Image
import pytest

from ecoscan.config import load_config
from ecoscan.image_processing.contracts import processing_contract
from ecoscan.services.execution_package import (
    allowed_source,
    ci_evidence,
    copy_authorized_photos,
    read_runtime_lock,
    verify_execution_archive,
    write_color_panels,
    write_execution_package,
)
from scripts import run_delivery_demo as launcher
from scripts import prepare_delivery_pack as pack_cli

ROOT = Path(__file__).resolve().parents[1]


def git(root, *args):
    return (
        subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.DEVNULL)
        .decode()
        .strip()
    )


@pytest.fixture
def repository(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    git(root, "init")
    git(root, "config", "user.name", "Technical Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    files = {
        "streamlit_app.py": 'print("technical fixture")\n',
        "pyproject.toml": '[project]\ndependencies=["numpy>=1.26"]\n',
        "requirements.txt": "numpy>=1.26\n",
        "README.md": "Project-owned source fixture",
        "config/education.json": '{"materials": {}}\n',
        "src/ecoscan/fixture.py": 'VALUE = "committed"\n',
        "models/semantic-v1/LICENSE-CLIP": "MIT License\nCopyright OpenAI\n",
        ".env": "PRIVATE_FIXTURE",
        ".streamlit/secrets.toml": "PRIVATE_FIXTURE",
        "config/user_profiles.json": "PRIVATE_FIXTURE",
        "data/raw/photo.png": "PRIVATE_FIXTURE",
        "backups/account.json": "PRIVATE_FIXTURE",
        "assets/unlicensed.png": "PRIVATE_FIXTURE",
        "models/semantic-v1/learning_seed.npz": "PRIVATE_FIXTURE",
    }
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
    settings = {
        "classes": ["metal"],
        "image_size": [224, 224],
        "confidence_threshold": 0.8,
        "allowed_extensions": [".png"],
        "directories": {"reports": "reports", "models": "models"},
        "model": {
            "engine": "semantic_onnx_assisted",
            "artifact_path": "models/semantic-v1/semantic.json",
            "remote_models_enabled": True,
            "confirmation_required": True,
        },
        "filters": {"default": "none"},
        "history": {"enabled": True},
    }
    (root / "config/settings.json").write_text(json.dumps(settings))
    folder = root / "models/semantic-v1"
    content = b"integrity fixture only, not a valid ONNX model"
    (folder / "encoder_00.part").write_bytes(content)
    (folder / "head.npz").write_bytes(b"head fixture")
    metadata = {
        "classes": ["metal", "unknown"],
        "threshold": 0.8,
        "encoder_file": "encoder.onnx",
        "processing": processing_contract(load_config(root / "config/settings.json")),
        "encoder_sha256": hashlib.sha256(content).hexdigest(),
        "head_sha256": hashlib.sha256(b"head fixture").hexdigest(),
        "parts": [{"name": "encoder_00.part", "sha256": hashlib.sha256(content).hexdigest()}],
    }
    (folder / "semantic.json").write_text(json.dumps(metadata))
    git(root, "add", ".")
    git(root, "commit", "-m", "technical fixture")
    lock = tmp_path / "runtime.lock"
    lock.write_text("numpy==2.5.4 --hash=sha256:" + "a" * 64 + "\n")
    return root, lock


def build(repository, output):
    root, lock = repository
    return write_execution_package(root, output, ref="HEAD", runtime_lock=lock, builder_root=ROOT)


def test_execution_archive_is_fixed_snapshot_without_private_material(repository, tmp_path):
    root, _ = repository
    sha = git(root, "rev-parse", "HEAD")
    (root / "src/ecoscan/fixture.py").write_text("UNCOMMITTED_PRIVATE_FIXTURE")
    paths = build(repository, tmp_path / "package")
    result = verify_execution_archive(paths["archive"])
    assert result["source_sha"] == sha and result["stage"] == "review_candidate_not_release"
    manifest = json.loads(paths["manifest"].read_text())
    assert manifest["release_ready"] is False
    assert manifest["offline_real_photo_copy"] == "manual_pending"
    assert set(manifest["external_acceptance"].values()) == {"manual_pending"}
    with zipfile.ZipFile(paths["archive"]) as archive:
        names = archive.namelist()
        assert all(
            not any(
                part in name
                for part in (
                    "secrets.toml",
                    ".env",
                    "user_profiles",
                    "learning_seed",
                    "data/raw",
                    "backups",
                    "assets/",
                )
            )
            for name in names
        )
        assert archive.read("ecoscan/src/ecoscan/fixture.py") == b'VALUE = "committed"\n'
        assert archive.read("ecoscan/config/education.json") == b'{"materials": {}}\n'
        settings = json.loads(archive.read("ecoscan/config/settings.json"))
        assert settings["model"]["confirmation_required"]
        assert not settings["model"]["remote_models_enabled"] and not settings["history"]["enabled"]
        assert "no native exe" in manifest["execution"]["method"]
        assert b"Python **3.12**" in archive.read("ecoscan/README_EXECUCAO.md")
    digest = hashlib.sha256(paths["archive"].read_bytes()).hexdigest()
    assert paths["checksums"].read_text().startswith(digest)


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        "config/user_profiles.json",
        ".streamlit/secrets.toml",
        "reports/backup.zip",
        "assets/unknown.png",
        "models/semantic-v1/learning_seed.json",
    ],
)
def test_allowlist_rejects_private_or_unlicensed_paths(path):
    assert not allowed_source(path)


def test_bad_hash_license_and_committed_symlink_fail(repository, tmp_path):
    root, _ = repository
    (root / "models/semantic-v1/head.npz").write_bytes(b"corrupt")
    git(root, "add", ".")
    git(root, "commit", "-m", "corrupt artifact")
    with pytest.raises(ValueError, match="Head checksum"):
        build(repository, tmp_path / "bad-hash")
    git(root, "reset", "--hard", "HEAD~1")
    (root / "models/semantic-v1/LICENSE-CLIP").unlink()
    git(root, "add", "-u")
    git(root, "commit", "-m", "missing license")
    with pytest.raises(FileNotFoundError):
        build(repository, tmp_path / "bad-license")
    git(root, "reset", "--hard", "HEAD~1")
    (root / "src/ecoscan/link.py").symlink_to(tmp_path / "outside")
    git(root, "add", ".")
    git(root, "commit", "-m", "unsafe link")
    with pytest.raises(ValueError, match="Links/submodules"):
        build(repository, tmp_path / "link")


def test_archive_extra_file_or_tampered_bytes_are_rejected(repository, tmp_path):
    paths = build(repository, tmp_path / "source-pack")
    with zipfile.ZipFile(paths["archive"]) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    for case in ("extra", "changed"):
        changed = dict(contents)
        if case == "extra":
            changed["ecoscan/.streamlit/secrets.toml"] = b"not real, forbidden anyway"
        else:
            changed["ecoscan/streamlit_app.py"] = b"changed"
        target = tmp_path / (case + ".zip")
        with zipfile.ZipFile(target, "w") as archive:
            for name, data in changed.items():
                archive.writestr(name, data)
        with pytest.raises(ValueError):
            verify_execution_archive(target)


def test_unpinned_lock_or_ci_approval_shortcut_are_refused(tmp_path):
    with pytest.raises(ValueError):
        read_runtime_lock(b"numpy>=1.26\n", {"project": {"dependencies": ["numpy>=1.26"]}})
    path = tmp_path / "ci.json"
    path.write_text(json.dumps({"approved": True, "token": "synthetic-only"}))
    with pytest.raises(ValueError):
        ci_evidence(path, "a" * 40)


@pytest.mark.parametrize(
    "extra",
    [" --index-url=https://synthetic.invalid/private", " # private-note", "\n# private-note"],
)
def test_delivery_lock_rejects_installer_urls_options_and_comments(extra):
    data = ("numpy==2.5.4 --hash=sha256:" + "a" * 64 + extra + "\n").encode()
    with pytest.raises(ValueError):
        read_runtime_lock(data, {"project": {"dependencies": ["numpy>=1.26"]}})


def test_invalid_archive_cli_refuses_without_echoing_input_path(tmp_path, capsys):
    archive = tmp_path / "private-input-name.zip"
    archive.write_bytes(b"not a ZIP")
    assert pack_cli.main(["verify", str(archive)]) == 1
    output = capsys.readouterr().out
    assert "BadZipFile" in output and "private-input-name" not in output


def test_launcher_does_not_borrow_service_credentials_or_kill_other_apps(monkeypatch):
    monkeypatch.setenv("ECOSCAN_SUPABASE_SERVICE_KEY", "synthetic-only")
    monkeypatch.setenv("ECOSCAN_SUPABASE_URL", "https://example.supabase.co")
    env = launcher.demo_environment(ROOT)
    assert "ECOSCAN_SUPABASE_SERVICE_KEY" not in env and "ECOSCAN_SUPABASE_URL" not in env
    assert env["ECOSCAN_REMOTE_MODELS"] == "false"
    command = launcher.command(ROOT, 8512, False)
    assert "--server.address=127.0.0.1" in command
    assert "--server.port=8512" in command and not any(
        "restart" in token or "taskkill" in token for token in command
    )
    assert any("delivery_demo.toml" in token for token in command)


def test_generated_ui_panels_do_not_copy_source_images_or_become_photo_evidence(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/disposal_targets.json").write_text(
        json.dumps(
            {
                "metal": {
                    "asset_path": "assets/disposal_targets/metal_yellow_bin.png",
                    "bin_color_hex": "#f2bc28",
                }
            }
        )
    )
    panels = write_color_panels(tmp_path)
    assert panels == ["assets/disposal_targets/metal_yellow_bin.png"]
    with Image.open(tmp_path / panels[0]) as image:
        assert image.getpixel((80, 80)) == (242, 188, 40)
    assert not (tmp_path / "examples").exists()
    (tmp_path / "config/disposal_targets.json").write_text(
        json.dumps({"metal": {"asset_path": "../../outside.png", "bin_color_hex": "#f2bc28"}})
    )
    with pytest.raises(ValueError, match="Invalid color panel"):
        write_color_panels(tmp_path)


def test_reviewed_photo_copy_is_exact_and_rejects_unapproved_or_outside_input(tmp_path):
    source = tmp_path / "images"
    source.mkdir()
    stage = tmp_path / "stage"
    stage.mkdir()
    image = source / "fixture.png"
    Image.new("RGB", (64, 64), "green").save(image)
    row = {
        "path": "fixture.png",
        "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "source_kind": "technical_fixture",
        "license": "CC0-1.0",
        "attribution": "Technical fixture",
        "distribution_allowed": True,
        "no_personal_data": True,
    }
    manifest = tmp_path / "images.json"
    manifest.write_text(json.dumps({"images": [row]}))
    copied = copy_authorized_photos(stage, source, manifest)
    assert copied[0]["source_kind"] == "technical_fixture"
    assert (stage / copied[0]["path"]).read_bytes() == image.read_bytes()
    row["distribution_allowed"] = False
    manifest.write_text(json.dumps({"images": [row]}))
    with pytest.raises(ValueError):
        copy_authorized_photos(stage, source, manifest)
    row["distribution_allowed"] = True
    row["path"] = "../outside.png"
    manifest.write_text(json.dumps({"images": [row]}))
    with pytest.raises(ValueError):
        copy_authorized_photos(stage, source, manifest)
