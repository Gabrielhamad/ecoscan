from __future__ import annotations

import hashlib
import json
import random
import shutil
from dataclasses import dataclass
from pathlib import Path

from ecoscan.config import AppConfig


@dataclass(frozen=True)
class SplitRecord:
    class_id: str
    source_path: str
    target_path: str
    split: str
    sha256: str


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _image_files(class_dir: Path, allowed_extensions: frozenset[str] | set[str]) -> list[Path]:
    return sorted(
        path for path in class_dir.iterdir()
        if path.is_file() and path.suffix.lower() in allowed_extensions
    )


def _safe_clear_split_dir(path: Path, project_root: Path) -> None:
    resolved = path.resolve()
    if not str(resolved).startswith(str(project_root.resolve())):
        raise ValueError(f"Refusing to clear directory outside project: {resolved}")
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _select_split(index: int, total: int, ratios: dict[str, float]) -> str:
    train_cutoff = round(total * ratios["train"])
    validation_cutoff = train_cutoff + round(total * ratios["validation"])
    if index < train_cutoff:
        return "train"
    if index < validation_cutoff:
        return "validation"
    return "test"


def _normalize_ratios(ratios: dict[str, float]) -> dict[str, float]:
    required = {"train", "validation", "test"}
    if set(ratios) != required:
        raise ValueError("Split ratios must contain train, validation and test.")
    total = sum(float(value) for value in ratios.values())
    if total <= 0:
        raise ValueError("Split ratios must sum to a positive value.")
    return {key: float(value) / total for key, value in ratios.items()}


def split_dataset(
    config: AppConfig,
    *,
    source_dir: Path | None = None,
    overwrite: bool = False,
) -> list[SplitRecord]:
    ratios = _normalize_ratios(config.dataset_split)
    if source_dir:
        raw_dir = source_dir if source_dir.is_absolute() else config.project_root / source_dir
        raw_dir = raw_dir.resolve()
    else:
        raw_dir = config.directories["raw_data"]
    split_dirs = {
        "train": config.directories["train_data"],
        "validation": config.directories["validation_data"],
        "test": config.directories["test_data"],
    }

    if overwrite:
        for split_dir in split_dirs.values():
            _safe_clear_split_dir(split_dir, config.project_root)
    else:
        for split_dir in split_dirs.values():
            if split_dir.exists() and any(child.name != ".gitkeep" for child in split_dir.iterdir()):
                raise FileExistsError(f"Split directory is not empty: {split_dir}. Use --overwrite.")

    rng = random.Random(config.random_seed)
    records: list[SplitRecord] = []
    duplicate_split_by_hash: dict[str, str] = {}

    for class_id in config.classes:
        class_dir = raw_dir / class_id
        if not class_dir.exists():
            continue
        files = _image_files(class_dir, config.allowed_extensions)
        rng.shuffle(files)

        for index, source in enumerate(files):
            digest = _hash_file(source)
            split = duplicate_split_by_hash.get(digest)
            if split is None:
                split = _select_split(index, len(files), ratios)
                duplicate_split_by_hash[digest] = split

            target_dir = split_dirs[split] / class_id
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / source.name
            shutil.copy2(source, target)
            records.append(
                SplitRecord(
                    class_id=class_id,
                    source_path=source.relative_to(config.project_root).as_posix(),
                    target_path=target.relative_to(config.project_root).as_posix(),
                    split=split,
                    sha256=digest,
                )
            )

    report_dir = config.directories["reports"] / "dataset_split"
    report_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = report_dir / "split_manifest.json"
    manifest_path.write_text(
        json.dumps([record.__dict__ for record in records], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return records
