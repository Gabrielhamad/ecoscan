"""Offline integrity checks, not a database export or restoration tool."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path


MANIFEST = "integrity.json"
BUCKETS = ("ecoscan-contributions", "ecoscan-civic-evidence")


def _is_link(path: Path) -> bool:
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _inventory(root: Path) -> dict[str, dict]:
    if _is_link(root) or not root.is_dir():
        raise ValueError("Diretorio de backup invalido.")
    files = {}
    for path in _entries(root):
        if _is_link(path):
            raise ValueError("Links nao sao permitidos no backup.")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError("Backup contem entrada que nao e arquivo regular.")
        name = path.relative_to(root).as_posix()
        if name == MANIFEST:
            continue
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        files[name] = {"bytes": path.stat().st_size, "sha256": digest}
    if files.get("database.sql", {}).get("bytes", 0) == 0:
        raise ValueError("Exportacao database.sql ausente ou vazia.")
    for bucket in BUCKETS:
        if not (root / "storage" / bucket).is_dir():
            raise ValueError("Falta diretorio de um bucket privado esperado.")
    return files


def _entries(root: Path):
    def fail(error: OSError):
        raise error

    # Reject linked directories before os.walk can enter them (including junctions).
    for directory, subdirs, filenames in os.walk(root, onerror=fail, followlinks=False):
        for name in sorted(subdirs):
            path = Path(directory) / name
            if _is_link(path):
                raise ValueError("Links nao sao permitidos no backup.")
        for name in sorted(filenames):
            yield Path(directory) / name


def seal_backup(root: Path, revision: str) -> int:
    """Seal a completed, quiescent local export without overwriting a previous seal."""
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise ValueError("Informe o SHA Git completo da revisao exportada.")
    files = _inventory(root)
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "revision": revision,
        "files": files,
    }
    with (root / MANIFEST).open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=True, indent=2)
        stream.write("\n")
    return len(files)


def verify_backup(root: Path) -> int:
    """Detect missing, added or changed files without reading paths from the manifest."""
    actual = _inventory(root)
    with (root / MANIFEST).open(encoding="utf-8") as stream:
        manifest = json.load(stream)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("Formato de manifesto nao suportado.")
    expected = manifest.get("files")
    if not isinstance(expected, dict) or expected != actual:
        raise ValueError("Integridade divergente: arquivo ausente, adicional ou alterado.")
    return len(actual)
