from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image, UnidentifiedImageError

from ecoscan.config import AppConfig
from ecoscan.image_processing.validation import ImageValidationError


MANIFEST_FIELDS = [
    "timestamp_utc",
    "status",
    "class_id",
    "original_name",
    "saved_path",
    "duplicate_of",
    "sha256",
    "width",
    "height",
    "file_size_bytes",
    "source_note",
    "message",
]


class DatasetIngestionError(ValueError):
    """Raised when dataset intake cannot be completed."""


@dataclass(frozen=True)
class IncomingImage:
    name: str
    data: bytes
    source_note: str = ""


@dataclass(frozen=True)
class DatasetIngestionResult:
    timestamp_utc: str
    status: str
    class_id: str
    original_name: str
    saved_path: str
    duplicate_of: str
    sha256: str
    width: int | None
    height: int | None
    file_size_bytes: int
    source_note: str
    message: str


@dataclass(frozen=True)
class _ImageInspection:
    width: int
    height: int
    image_format: str | None


def ingestion_manifest_path_from_config(config: AppConfig) -> Path:
    return config.directories["reports"] / "dataset_uploads" / "upload_manifest.csv"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _extension_for_name(name: str, allowed_extensions: frozenset[str]) -> str:
    suffix = Path(name or "").suffix.lower()
    if suffix not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise ImageValidationError(f"Formato '{suffix or 'sem extensão'}' não suportado. Use: {allowed}.")
    return suffix


def _safe_stem(name: str) -> str:
    stem = Path(name or "imagem").stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return (stem or "imagem")[:52]


def _inspect_image_bytes(data: bytes, min_size: tuple[int, int]) -> _ImageInspection:
    if not data:
        raise ImageValidationError("Arquivo vazio.")

    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
        with Image.open(BytesIO(data)) as image:
            width, height = image.size
            if width < min_size[0] or height < min_size[1]:
                raise ImageValidationError(
                    f"Imagem muito pequena: {width}x{height}. Mínimo: {min_size[0]}x{min_size[1]}."
                )
            return _ImageInspection(width=width, height=height, image_format=image.format)
    except ImageValidationError:
        raise
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageValidationError("Arquivo corrompido ou ilegível.") from exc


def _build_hash_index(dataset_root: Path, allowed_extensions: frozenset[str]) -> dict[str, Path]:
    hashes: dict[str, Path] = {}
    if not dataset_root.exists():
        return hashes

    for path in sorted(dataset_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in allowed_extensions:
            continue
        try:
            hashes.setdefault(_hash_file(path), path)
        except OSError:
            continue
    return hashes


def _target_path(dataset_root: Path, class_id: str, original_name: str, digest: str, extension: str) -> Path:
    target_dir = dataset_root / class_id
    target_dir.mkdir(parents=True, exist_ok=True)
    base_name = f"{_safe_stem(original_name)}-{digest[:12]}"
    candidate = target_dir / f"{base_name}{extension}"
    counter = 2
    while candidate.exists():
        candidate = target_dir / f"{base_name}-{counter}{extension}"
        counter += 1
    return candidate


def _append_manifest_rows(manifest_path: Path, rows: list[DatasetIngestionResult]) -> None:
    if not rows:
        return
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not manifest_path.exists()
    with manifest_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_FIELDS)
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _result(
    *,
    status: str,
    class_id: str,
    original_name: str,
    saved_path: Path | None,
    duplicate_of: Path | None,
    sha256: str,
    width: int | None,
    height: int | None,
    file_size_bytes: int,
    source_note: str,
    message: str,
    root_for_relative_paths: Path,
) -> DatasetIngestionResult:
    return DatasetIngestionResult(
        timestamp_utc=_utc_now(),
        status=status,
        class_id=class_id,
        original_name=original_name,
        saved_path=_relative(saved_path, root_for_relative_paths) if saved_path else "",
        duplicate_of=_relative(duplicate_of, root_for_relative_paths) if duplicate_of else "",
        sha256=sha256,
        width=width,
        height=height,
        file_size_bytes=file_size_bytes,
        source_note=source_note,
        message=message,
    )


def ingest_uploaded_images(
    config: AppConfig,
    class_id: str,
    images: Iterable[IncomingImage],
    *,
    dataset_dir: str | Path | None = None,
    manifest_path: str | Path | None = None,
) -> list[DatasetIngestionResult]:
    if class_id not in config.classes:
        allowed = ", ".join(config.classes)
        raise DatasetIngestionError(f"Classe '{class_id}' não está configurada. Classes ativas: {allowed}.")

    dataset_root = Path(dataset_dir).resolve() if dataset_dir else config.directories["raw_data"]
    manifest = Path(manifest_path).resolve() if manifest_path else ingestion_manifest_path_from_config(config)
    existing_hashes = _build_hash_index(dataset_root, config.allowed_extensions)
    results: list[DatasetIngestionResult] = []

    for image in images:
        original_name = image.name or "imagem"
        source_note = image.source_note
        data = bytes(image.data)
        digest = _sha256_bytes(data) if data else ""
        try:
            extension = _extension_for_name(original_name, config.allowed_extensions)
            inspection = _inspect_image_bytes(data, config.min_image_size)
            duplicate_path = existing_hashes.get(digest)
            if duplicate_path:
                results.append(
                    _result(
                        status="duplicate",
                        class_id=class_id,
                        original_name=original_name,
                        saved_path=None,
                        duplicate_of=duplicate_path,
                        sha256=digest,
                        width=inspection.width,
                        height=inspection.height,
                        file_size_bytes=len(data),
                        source_note=source_note,
                        message="Imagem já existe no dataset bruto.",
                        root_for_relative_paths=config.project_root,
                    )
                )
                continue

            target = _target_path(dataset_root, class_id, original_name, digest, extension)
            target.write_bytes(data)
            existing_hashes[digest] = target
            results.append(
                _result(
                    status="saved",
                    class_id=class_id,
                    original_name=original_name,
                    saved_path=target,
                    duplicate_of=None,
                    sha256=digest,
                    width=inspection.width,
                    height=inspection.height,
                    file_size_bytes=len(data),
                    source_note=source_note,
                    message="Imagem salva no dataset bruto para curadoria.",
                    root_for_relative_paths=config.project_root,
                )
            )
        except ImageValidationError as exc:
            results.append(
                _result(
                    status="rejected",
                    class_id=class_id,
                    original_name=original_name,
                    saved_path=None,
                    duplicate_of=None,
                    sha256=digest,
                    width=None,
                    height=None,
                    file_size_bytes=len(data),
                    source_note=source_note,
                    message=str(exc),
                    root_for_relative_paths=config.project_root,
                )
            )

    _append_manifest_rows(manifest, results)
    return results


def ingest_image_files(
    config: AppConfig,
    class_id: str,
    paths: Iterable[str | Path],
    *,
    dataset_dir: str | Path | None = None,
    manifest_path: str | Path | None = None,
    source_note: str = "folder-import",
) -> list[DatasetIngestionResult]:
    incoming = [
        IncomingImage(name=Path(path).name, data=Path(path).read_bytes(), source_note=source_note)
        for path in paths
        if Path(path).is_file()
    ]
    return ingest_uploaded_images(
        config,
        class_id,
        incoming,
        dataset_dir=dataset_dir,
        manifest_path=manifest_path,
    )
