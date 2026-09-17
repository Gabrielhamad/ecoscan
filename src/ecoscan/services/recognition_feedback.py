from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ecoscan.config import AppConfig
from ecoscan.image_processing.image_io import save_image


@dataclass(frozen=True)
class RecognitionFeedback:
    id: str
    timestamp_utc: str
    reporter_id: str
    reporter_name: str
    expected_class: str
    predicted_class: str | None
    top_class: str | None
    probability: float | None
    accepted: bool
    model_type: str
    filter_name: str
    segmentation_name: str
    source_kind: str
    note: str
    image_path: str


def feedback_dir_from_config(config: AppConfig) -> Path:
    return config.directories["reports"] / "recognition_feedback"


def feedback_manifest_path_from_config(config: AppConfig) -> Path:
    return feedback_dir_from_config(config) / "feedback.csv"


def append_recognition_feedback(
    config: AppConfig,
    result: Any,
    *,
    expected_class: str,
    reporter_id: str,
    reporter_name: str,
    source_kind: str,
    note: str = "",
) -> RecognitionFeedback:
    if expected_class not in (*config.classes, "out_of_scope", "unknown"):
        allowed = ", ".join(config.classes)
        raise ValueError(f"Classe esperada inválida: {expected_class}. Classes: {allowed}")

    feedback_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    safe_expected = expected_class.replace("/", "_")
    safe_predicted = (result.predicted_class or result.top_class or "uncertain").replace("/", "_")
    output_dir = feedback_dir_from_config(config)
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    image_path = image_dir / f"{feedback_id}_{safe_expected}_from_{safe_predicted}.jpg"
    save_image(result.pipeline.loaded.array, image_path)

    feedback = RecognitionFeedback(
        id=feedback_id,
        timestamp_utc=timestamp,
        reporter_id=reporter_id,
        reporter_name=reporter_name,
        expected_class=expected_class,
        predicted_class=result.predicted_class,
        top_class=result.top_class,
        probability=result.probability,
        accepted=bool(result.accepted),
        model_type=result.model_type,
        filter_name=result.pipeline.filter_result.name,
        segmentation_name=result.pipeline.segmentation_result.name,
        source_kind=source_kind,
        note=note.strip(),
        image_path=str(image_path),
    )
    _append_csv(feedback_manifest_path_from_config(config), feedback)
    return feedback


def _append_csv(path: Path, feedback: RecognitionFeedback) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = asdict(feedback)
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def read_recognition_feedback(
    path: str | Path,
    *,
    limit: int | None = None,
) -> list[RecognitionFeedback]:
    manifest_path = Path(path)
    if not manifest_path.exists():
        return []

    rows: list[RecognitionFeedback] = []
    with manifest_path.open("r", newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            rows.append(
                RecognitionFeedback(
                    id=str(row.get("id", "")),
                    timestamp_utc=str(row.get("timestamp_utc", "")),
                    reporter_id=str(row.get("reporter_id", "")),
                    reporter_name=str(row.get("reporter_name", "")),
                    expected_class=str(row.get("expected_class", "")),
                    predicted_class=_optional_text(row.get("predicted_class")),
                    top_class=_optional_text(row.get("top_class")),
                    probability=_optional_float(row.get("probability")),
                    accepted=_optional_bool(row.get("accepted")),
                    model_type=str(row.get("model_type", "")),
                    filter_name=str(row.get("filter_name", "")),
                    segmentation_name=str(row.get("segmentation_name", "")),
                    source_kind=str(row.get("source_kind", "")),
                    note=str(row.get("note", "")),
                    image_path=str(row.get("image_path", "")),
                )
            )
    if limit is not None:
        return rows[-limit:]
    return rows


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_float(value: object) -> float | None:
    try:
        text = str(value or "").strip()
        return float(text) if text else None
    except ValueError:
        return None


def _optional_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "sim"}
