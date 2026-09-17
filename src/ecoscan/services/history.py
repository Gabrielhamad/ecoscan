from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ecoscan.config import AppConfig


@dataclass(frozen=True)
class HistoryEntry:
    id: str
    timestamp_utc: str
    source_path: str | None
    predicted_class: str | None
    top_class: str | None
    probability: float | None
    accepted: bool
    model_type: str
    filter_name: str
    segmentation_name: str
    environmental_category: str | None
    guidance_summary: str | None
    filter_decision: str | None = None
    filter_reason: str | None = None
    segmentation_decision: str | None = None
    segmentation_reason: str | None = None
    capture_quality_status: str | None = None
    capture_quality_score: int | None = None
    elements_count: int | None = None
    elements_warning: str | None = None


def history_path_from_config(config: AppConfig) -> Path:
    configured_path = Path(str(config.history.get("path", "logs/history.jsonl")))
    if configured_path.is_absolute():
        return configured_path
    return config.project_root / configured_path


def build_history_entry(result: Any, source_path: str | Path | None = None) -> HistoryEntry:
    guidance = result.guidance
    metadata = result.pipeline.metadata
    filter_meta = dict(metadata.get("filter", {}))
    segmentation_meta = dict(metadata.get("segmentation", {}))
    filter_decision = dict(filter_meta.get("decision") or {})
    segmentation_decision = dict(segmentation_meta.get("decision") or {})
    capture_quality = dict(metadata.get("capture_quality") or {})
    element_analysis = getattr(result.pipeline, "element_analysis", None)
    filter_name = str(filter_meta.get("name", ""))
    segmentation_name = str(segmentation_meta.get("name", ""))
    return HistoryEntry(
        id=str(uuid4()),
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        source_path=str(source_path) if source_path is not None else None,
        predicted_class=result.predicted_class,
        top_class=result.top_class,
        probability=result.probability,
        accepted=bool(result.accepted),
        model_type=result.model_type,
        filter_name=filter_name,
        segmentation_name=segmentation_name,
        environmental_category=guidance.environmental_category if guidance else None,
        guidance_summary=guidance.guidance if guidance else None,
        filter_decision=str(filter_decision.get("selected") or filter_name),
        filter_reason=str(filter_decision.get("reason") or filter_meta.get("explanation") or ""),
        segmentation_decision=str(segmentation_decision.get("selected") or segmentation_name),
        segmentation_reason=str(segmentation_decision.get("reason") or segmentation_meta.get("explanation") or ""),
        capture_quality_status=str(capture_quality.get("status") or ""),
        capture_quality_score=capture_quality.get("score"),
        elements_count=getattr(element_analysis, "significant_count", None),
        elements_warning=getattr(element_analysis, "warning", None),
    )


def append_history_entry(path: str | Path, entry: HistoryEntry) -> Path:
    history_path = Path(path)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    return history_path


def read_history(path: str | Path, *, limit: int | None = None) -> list[HistoryEntry]:
    history_path = Path(path)
    if not history_path.exists():
        return []

    entries: list[HistoryEntry] = []
    for line in history_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        allowed_fields = {field.name for field in fields(HistoryEntry)}
        entries.append(HistoryEntry(**{key: value for key, value in payload.items() if key in allowed_fields}))
    if limit is not None:
        return entries[-limit:]
    return entries


def clear_history(path: str | Path) -> None:
    history_path = Path(path)
    if history_path.exists():
        history_path.unlink()
