from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass
from pathlib import Path

from ecoscan.config import AppConfig


REVIEW_FIELDNAMES = [
    "relative_path",
    "class_id",
    "status",
    "suggested_class",
    "notes",
]


@dataclass(frozen=True)
class ReviewRow:
    relative_path: str
    class_id: str
    status: str
    suggested_class: str
    notes: str


def _iter_images(dataset_dir: Path, classes: tuple[str, ...], allowed_extensions: frozenset[str]) -> list[ReviewRow]:
    rows: list[ReviewRow] = []
    for class_id in classes:
        class_dir = dataset_dir / class_id
        if not class_dir.exists():
            continue
        for path in sorted(class_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in allowed_extensions:
                rows.append(
                    ReviewRow(
                        relative_path=path.relative_to(dataset_dir).as_posix(),
                        class_id=class_id,
                        status="accepted",
                        suggested_class="",
                        notes="",
                    )
                )
    return rows


def create_review_sheet(config: AppConfig, *, dataset_dir: Path | None = None, output_path: Path | None = None) -> Path:
    selected_dataset_dir = dataset_dir or config.directories["raw_data"]
    selected_output_path = output_path or config.directories["reports"] / "dataset_review" / "review_sheet.csv"
    rows = _iter_images(selected_dataset_dir, config.classes, config.allowed_extensions)

    selected_output_path.parent.mkdir(parents=True, exist_ok=True)
    with selected_output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=REVIEW_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)
    return selected_output_path


def _safe_clear(path: Path, project_root: Path) -> None:
    path = path.resolve()
    if not str(path).startswith(str(project_root.resolve())):
        raise ValueError(f"Refusing to clear directory outside project: {path}")
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def apply_review_sheet(
    config: AppConfig,
    *,
    review_path: Path,
    source_dir: Path | None = None,
    output_dir: Path | None = None,
    overwrite: bool = False,
) -> dict[str, int]:
    selected_source_dir = source_dir or config.directories["raw_data"]
    selected_output_dir = output_dir or config.directories["curated_data"]
    if overwrite:
        _safe_clear(selected_output_dir, config.project_root)
    selected_output_dir.mkdir(parents=True, exist_ok=True)

    counts = {"accepted": 0, "rejected": 0, "reclassified": 0, "missing": 0}
    with review_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            relative_path = row["relative_path"]
            status = row.get("status", "accepted").strip().lower()
            if status not in {"accepted", "rejected"}:
                status = "rejected"

            if status == "rejected":
                counts["rejected"] += 1
                continue

            source_path = selected_source_dir / relative_path
            if not source_path.exists():
                counts["missing"] += 1
                continue

            target_class = (row.get("suggested_class") or row.get("class_id") or "").strip()
            if target_class not in config.classes:
                counts["rejected"] += 1
                continue

            if target_class != row.get("class_id"):
                counts["reclassified"] += 1
            target_path = selected_output_dir / target_class / source_path.name
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
            counts["accepted"] += 1
    return counts

