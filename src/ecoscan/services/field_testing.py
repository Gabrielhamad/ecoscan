from __future__ import annotations

import csv
from collections import Counter
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from ecoscan.config import AppConfig
from ecoscan.services.operational_store import operational_store


VALID_RESULT_STATUSES = frozenset({"acertou", "errou", "inconclusivo"})


@dataclass(frozen=True)
class FieldTestRecord:
    id: str
    timestamp_utc: str
    tester_id: str
    tester_name: str
    device_kind: str
    capture_mode: str
    expected_class: str
    model_class: str | None
    result_status: str
    confidence: float | None
    note: str


@dataclass(frozen=True)
class FieldTestSummary:
    total: int
    correct_count: int
    wrong_count: int
    inconclusive_count: int
    mobile_count: int


def field_test_dir_from_config(config: AppConfig) -> Path:
    return config.directories["reports"] / "field_tests"


def field_test_manifest_path_from_config(config: AppConfig) -> Path:
    return field_test_dir_from_config(config) / "field_tests.csv"


def build_field_test_record(
    *,
    tester_id: str,
    tester_name: str,
    expected_class: str,
    result_status: str,
    device_kind: str,
    capture_mode: str,
    model_class: str | None = None,
    confidence: float | None = None,
    note: str = "",
) -> FieldTestRecord:
    clean_status = result_status.strip().lower()
    if clean_status not in VALID_RESULT_STATUSES:
        raise ValueError("Status de teste inválido: " + result_status)
    if len(note) > 600:
        raise ValueError("Use até 600 caracteres na observação do teste.")
    clean_confidence = None if confidence is None else max(0.0, min(1.0, float(confidence)))
    return FieldTestRecord(
        id=str(uuid4()),
        timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        tester_id=tester_id.strip(),
        tester_name=tester_name.strip(),
        device_kind=device_kind.strip() or "não informado",
        capture_mode=capture_mode.strip() or "não informado",
        expected_class=expected_class.strip(),
        model_class=_optional_text(model_class),
        result_status=clean_status,
        confidence=clean_confidence,
        note=note.strip(),
    )


def append_field_test_record(path: str | Path, record: FieldTestRecord) -> Path:
    store = operational_store()
    if store is not None:
        store.append("field_tests", asdict(record))
        return Path(path)
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    exists = manifest_path.exists()
    with manifest_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[field.name for field in fields(FieldTestRecord)])
        if not exists:
            writer.writeheader()
        writer.writerow(asdict(record))
    return manifest_path


def read_field_test_records(
    path: str | Path,
    *,
    tester_id: str | None = None,
    limit: int | None = None,
) -> list[FieldTestRecord]:
    store = operational_store()
    if store is not None:
        return [FieldTestRecord(**row) for row in store.read("field_tests", owner=tester_id, limit=limit)]
    manifest_path = Path(path)
    if not manifest_path.exists():
        return []

    rows: list[FieldTestRecord] = []
    with manifest_path.open("r", newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            record = FieldTestRecord(
                id=str(row.get("id", "")),
                timestamp_utc=str(row.get("timestamp_utc", "")),
                tester_id=str(row.get("tester_id", "")),
                tester_name=str(row.get("tester_name", "")),
                device_kind=str(row.get("device_kind", "")),
                capture_mode=str(row.get("capture_mode", "")),
                expected_class=str(row.get("expected_class", "")),
                model_class=_optional_text(row.get("model_class")),
                result_status=str(row.get("result_status", "")),
                confidence=_optional_float(row.get("confidence")),
                note=str(row.get("note", "")),
            )
            if tester_id is None or record.tester_id == tester_id:
                rows.append(record)
    if limit is not None:
        return rows[-limit:]
    return rows


def summarize_field_tests(records: Iterable[FieldTestRecord]) -> FieldTestSummary:
    items = tuple(records)
    return FieldTestSummary(
        total=len(items),
        correct_count=sum(1 for item in items if item.result_status == "acertou"),
        wrong_count=sum(1 for item in items if item.result_status == "errou"),
        inconclusive_count=sum(1 for item in items if item.result_status == "inconclusivo"),
        mobile_count=sum(1 for item in items if item.device_kind.lower() == "celular"),
    )


def field_test_rows(
    records: Iterable[FieldTestRecord],
    class_labels: dict[str, str],
    *,
    limit: int = 30,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in tuple(records)[-limit:]:
        rows.append(
            {
                "data_utc": item.timestamp_utc,
                "testador": item.tester_name or item.tester_id,
                "dispositivo": item.device_kind,
                "captura": item.capture_mode,
                "esperado": class_labels.get(item.expected_class, item.expected_class),
                "modelo": class_labels.get(item.model_class or "", item.model_class or "não reconheceu"),
                "resultado": item.result_status,
                "confiança": item.confidence,
                "observação": item.note,
            }
        )
    return list(reversed(rows))


def field_test_class_rows(
    records: Iterable[FieldTestRecord],
    class_labels: dict[str, str],
) -> list[dict[str, Any]]:
    items = tuple(records)
    expected_counts: Counter[str] = Counter(item.expected_class for item in items)
    wrong_counts: Counter[str] = Counter(item.expected_class for item in items if item.result_status == "errou")
    inconclusive_counts: Counter[str] = Counter(
        item.expected_class for item in items if item.result_status == "inconclusivo"
    )
    rows: list[dict[str, Any]] = []
    for class_id, total in expected_counts.most_common():
        wrong = wrong_counts[class_id]
        inconclusive = inconclusive_counts[class_id]
        rows.append(
            {
                "classe": class_labels.get(class_id, class_id),
                "testes": total,
                "acertos": total - wrong - inconclusive,
                "erros": wrong,
                "inconclusivos": inconclusive,
                "prioridade": "alta" if wrong + inconclusive >= 3 else "média" if wrong + inconclusive else "baixa",
            }
        )
    return sorted(rows, key=lambda row: (-int(row["erros"]) - int(row["inconclusivos"]), str(row["classe"])))


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_float(value: object) -> float | None:
    try:
        text = str(value or "").strip()
        return float(text) if text else None
    except ValueError:
        return None
