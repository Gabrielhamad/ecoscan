from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ecoscan.config import AppConfig


VALID_REVIEW_DECISIONS = frozenset({"encaminhar", "arquivar", "solicitar_nova_foto"})


@dataclass(frozen=True)
class CivicReportRecord:
    id: str
    timestamp_utc: str
    location_note: str
    description: str
    contact: str
    evidence_path: str
    evidence_sha256: str
    source_kind: str
    verification_status: str
    detected_class: str | None
    top_class: str | None
    probability: float | None
    filter_name: str
    filter_decision: str
    segmentation_name: str
    segmentation_decision: str
    capture_quality_status: str
    capture_quality_score: int | None
    elements_count: int | None
    verifier_note: str
    submitted_by: str = ""


@dataclass(frozen=True)
class CivicReportReview:
    id: str
    timestamp_utc: str
    report_id: str
    admin_user_id: str
    decision: str
    note: str


def civic_reports_path_from_config(config: AppConfig) -> Path:
    return config.directories["reports"] / "civic_reports" / "reports_manifest.csv"


def civic_evidence_dir_from_config(config: AppConfig) -> Path:
    return config.directories["reports"] / "civic_reports" / "evidence"


def civic_report_reviews_path_from_config(config: AppConfig) -> Path:
    return config.directories["reports"] / "civic_reports" / "review_manifest.csv"


def save_civic_report_evidence(
    config: AppConfig,
    *,
    original_name: str,
    data: bytes,
) -> Path:
    evidence_dir = civic_evidence_dir_from_config(config)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(original_name or "evidence.jpg").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        suffix = ".jpg"
    digest = hashlib.sha256(data).hexdigest()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{stamp}_{digest[:12]}_{_sanitize_filename(original_name)}{suffix}"
    path = evidence_dir / filename
    path.write_bytes(data)
    return path


def build_civic_report_record(
    result: Any,
    *,
    evidence_path: Path,
    location_note: str,
    description: str,
    contact: str = "",
    source_kind: str = "upload",
    submitted_by: str = "",
) -> CivicReportRecord:
    metadata = getattr(result.pipeline, "metadata", {})
    filter_meta = dict(metadata.get("filter") or {})
    segmentation_meta = dict(metadata.get("segmentation") or {})
    filter_decision = dict(filter_meta.get("decision") or {})
    segmentation_decision = dict(segmentation_meta.get("decision") or {})
    capture_quality = dict(metadata.get("capture_quality") or {})
    element_analysis = getattr(result.pipeline, "element_analysis", None)
    verification_status, verifier_note = classify_report_verification(result)

    return CivicReportRecord(
        id=str(uuid4()),
        timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        location_note=location_note.strip(),
        description=description.strip(),
        contact=contact.strip(),
        evidence_path=str(evidence_path),
        evidence_sha256=hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
        source_kind=source_kind,
        verification_status=verification_status,
        detected_class=result.predicted_class,
        top_class=result.top_class,
        probability=result.probability,
        filter_name=str(filter_meta.get("name") or ""),
        filter_decision=str(filter_decision.get("selected") or filter_meta.get("name") or ""),
        segmentation_name=str(segmentation_meta.get("name") or ""),
        segmentation_decision=str(segmentation_decision.get("selected") or segmentation_meta.get("name") or ""),
        capture_quality_status=str(capture_quality.get("status") or ""),
        capture_quality_score=capture_quality.get("score"),
        elements_count=getattr(element_analysis, "significant_count", None),
        verifier_note=verifier_note,
        submitted_by=submitted_by.strip(),
    )


def classify_report_verification(result: Any) -> tuple[str, str]:
    metadata = getattr(getattr(result, "pipeline", None), "metadata", {})
    capture_quality = metadata.get("capture_quality") if isinstance(metadata, dict) else {}
    capture_status = str((capture_quality or {}).get("status") or "").strip().lower()
    elements_count = getattr(getattr(getattr(result, "pipeline", None), "element_analysis", None), "significant_count", 0)

    if capture_status == "retake" or int(elements_count or 0) == 0:
        return (
            "imagem_insuficiente",
            "A imagem foi registrada, mas a triagem recomenda nova foto antes de encaminhamento.",
        )
    if getattr(result, "accepted", False):
        return (
            "triagem_consistente",
            "A imagem possui qualidade suficiente e o reconhecimento encontrou um resíduo compatível.",
        )
    return (
        "triagem_inconclusiva",
        "A imagem passou pelo processamento, mas o reconhecimento não teve confiança suficiente.",
    )


def append_civic_report(path: str | Path, record: CivicReportRecord) -> Path:
    if record.submitted_by.startswith("visitor_"):
        raise ValueError("Entre em uma conta para enviar relatos.")
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    exists = report_path.exists()
    with report_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[field.name for field in fields(CivicReportRecord)])
        if not exists:
            writer.writeheader()
        writer.writerow(asdict(record))
    return report_path


def read_civic_reports(path: str | Path, *, limit: int | None = None) -> list[CivicReportRecord]:
    report_path = Path(path)
    if not report_path.exists():
        return []
    rows: list[CivicReportRecord] = []
    allowed_fields = {field.name for field in fields(CivicReportRecord)}
    with report_path.open("r", newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            payload = {key: row.get(key, "") for key in allowed_fields}
            payload["probability"] = _optional_float(payload.get("probability"))
            payload["capture_quality_score"] = _optional_int(payload.get("capture_quality_score"))
            payload["elements_count"] = _optional_int(payload.get("elements_count"))
            rows.append(CivicReportRecord(**payload))
    if limit is not None:
        return rows[-limit:]
    return rows


def build_civic_report_review(
    *,
    report_id: str,
    admin_user_id: str,
    decision: str,
    note: str = "",
) -> CivicReportReview:
    clean_decision = decision.strip().lower()
    if clean_decision not in VALID_REVIEW_DECISIONS:
        raise ValueError("Invalid civic report review decision: " + clean_decision)
    return CivicReportReview(
        id=str(uuid4()),
        timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        report_id=report_id.strip(),
        admin_user_id=admin_user_id.strip(),
        decision=clean_decision,
        note=note.strip(),
    )


def append_civic_report_review(path: str | Path, review: CivicReportReview) -> Path:
    review_path = Path(path)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    exists = review_path.exists()
    with review_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[field.name for field in fields(CivicReportReview)])
        if not exists:
            writer.writeheader()
        writer.writerow(asdict(review))
    return review_path


def read_civic_report_reviews(path: str | Path, *, limit: int | None = None) -> list[CivicReportReview]:
    review_path = Path(path)
    if not review_path.exists():
        return []
    rows: list[CivicReportReview] = []
    allowed_fields = {field.name for field in fields(CivicReportReview)}
    with review_path.open("r", newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            payload = {key: row.get(key, "") for key in allowed_fields}
            rows.append(CivicReportReview(**payload))
    if limit is not None:
        return rows[-limit:]
    return rows


def latest_reviews_by_report(reviews: list[CivicReportReview]) -> dict[str, CivicReportReview]:
    latest: dict[str, CivicReportReview] = {}
    for review in reviews:
        latest[review.report_id] = review
    return latest


def _sanitize_filename(value: str) -> str:
    stem = Path(value or "evidence").stem
    clean = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower()
    return clean[:48] or "evidence"


def _optional_float(value: Any) -> float | None:
    try:
        text = str(value or "").strip()
        return float(text) if text else None
    except ValueError:
        return None


def _optional_int(value: Any) -> int | None:
    try:
        text = str(value or "").strip()
        return int(text) if text else None
    except ValueError:
        return None
