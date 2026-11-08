"""Local APS launcher/verifier; no service credentials or deployment operations."""

from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_files(root: Path) -> dict:
    manifest_path = root / "delivery_manifest.json"
    if not manifest_path.exists():
        return {"stage": "source_checkout", "files_verified": 0}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in manifest["files"]:
        relative = Path(row["path"])
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or "\\" in row["path"]
            or not (root / relative).resolve().is_relative_to(root.resolve())
            or (root / relative).is_symlink()
        ):
            raise ValueError("Unsafe manifest file path")
        if digest(root / relative) != row["sha256"]:
            raise ValueError("Package file checksum mismatch")
    return {
        "stage": manifest["stage"],
        "source_sha": manifest["source_sha"],
        "files_verified": len(manifest["files"]),
    }


def verify_model(root: Path) -> dict:
    sys.path.insert(0, str(root / "src"))
    from ecoscan.classification.semantic_onnx import file_digest, resolve_encoder
    from ecoscan.config import load_config
    from ecoscan.image_processing.contracts import processing_contract

    config = load_config(root / "config/settings.json")
    if config.model["artifact_path"] != "models/semantic-v1/semantic.json":
        raise ValueError("Unexpected configured model")
    folder = root / "models/semantic-v1"
    metadata = json.loads((folder / "semantic.json").read_text())
    if metadata["processing"] != processing_contract(config):
        raise ValueError("Processing contract mismatch")
    if file_digest(folder / "head.npz") != metadata["head_sha256"]:
        raise ValueError("Head checksum mismatch")
    if set(metadata["classes"]) != set(config.classes) | {"unknown"}:
        raise ValueError("Model classes mismatch")
    encoder = resolve_encoder(folder, metadata)
    return {
        "metadata_sha256": digest(folder / "semantic.json"),
        "head_sha256": metadata["head_sha256"],
        "encoder_sha256": digest(encoder),
        "processing_sha256": metadata["processing"]["sha256"],
    }


def verify_installed(root: Path) -> None:
    lock = root / "requirements.delivery.lock"
    if not lock.exists():
        return
    for line in lock.read_text().replace("\\\n", " ").splitlines():
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^ ;]+)", line)
        if not match or version(match[1]) != match[2]:
            raise ValueError("Installed dependency differs from the delivery lock")


def demo_environment(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    # Explicit local demonstration profile; never borrow hosting credentials.
    for key in tuple(env):
        if key.startswith("ECOSCAN_"):
            env.pop(key)
    env.update(
        ECOSCAN_COMMUNITY_ENABLED="false",
        ECOSCAN_OPERATIONS_ENABLED="false",
        ECOSCAN_REMOTE_MODELS="false",
        PYTHONPATH=str(root / "src"),
    )
    return env


def command(root: Path, port: int, lan: bool) -> list[str]:
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(root / "streamlit_app.py"),
        "--server.address=" + ("0.0.0.0" if lan else "127.0.0.1"),
        f"--server.port={port}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--secrets.files=" + str(root / "config/delivery_demo.toml"),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["verify", "serve"], nargs="?", default="serve")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument(
        "--lan", action="store_true", help="Expose only when needed on the presentation LAN"
    )
    args = parser.parse_args(argv)
    try:
        if sys.version_info[:2] != (3, 12):
            raise ValueError("Python 3.12 is required")
        if not 1024 <= args.port <= 65535:
            raise ValueError("Invalid port")
        result = verify_files(ROOT)
        verify_installed(ROOT)
        result["model"] = verify_model(ROOT)
        result["python"] = ".".join(map(str, sys.version_info[:3]))
        print(json.dumps(result))
        if args.action == "verify":
            return 0
        print("Abrir http://localhost:" + str(args.port) + "; Ctrl+C encerra esta instancia.")
        return subprocess.call(
            command(ROOT, args.port, args.lan), cwd=ROOT, env=demo_environment(ROOT)
        )
    except (OSError, ValueError, KeyError, ImportError) as exc:
        print(
            f"Execucao recusada ({type(exc).__name__}). Confira Python 3.12, dependencias e checksums; veja README_EXECUCAO.md."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
