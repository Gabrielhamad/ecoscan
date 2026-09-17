from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from ecoscan.services.history import HistoryEntry
from ecoscan.services.recognition_feedback import RecognitionFeedback


@dataclass(frozen=True)
class RecognitionQualitySummary:
    analysis_count: int
    accepted_count: int
    uncertain_count: int
    low_confidence_count: int
    average_confidence: float | None
    feedback_count: int
    correction_pair_count: int


def build_recognition_quality_summary(
    history_entries: Iterable[HistoryEntry],
    feedback_entries: Iterable[RecognitionFeedback],
    *,
    low_confidence_threshold: float = 0.72,
) -> RecognitionQualitySummary:
    history = tuple(history_entries)
    feedback = tuple(feedback_entries)
    probabilities = [entry.probability for entry in history if entry.probability is not None]
    accepted_count = sum(1 for entry in history if entry.accepted)
    uncertain_count = len(history) - accepted_count
    low_confidence_count = sum(
        1
        for entry in history
        if entry.probability is not None and entry.probability < low_confidence_threshold
    )
    correction_pair_count = sum(1 for item in feedback if _feedback_has_mismatch(item))
    return RecognitionQualitySummary(
        analysis_count=len(history),
        accepted_count=accepted_count,
        uncertain_count=uncertain_count,
        low_confidence_count=low_confidence_count,
        average_confidence=(sum(probabilities) / len(probabilities)) if probabilities else None,
        feedback_count=len(feedback),
        correction_pair_count=correction_pair_count,
    )


def class_quality_rows(
    history_entries: Iterable[HistoryEntry],
    class_labels: dict[str, str],
    *,
    low_confidence_threshold: float = 0.72,
) -> list[dict[str, object]]:
    history = tuple(history_entries)
    classes = sorted({entry.top_class or entry.predicted_class or "__uncertain__" for entry in history})
    rows: list[dict[str, object]] = []
    for class_id in classes:
        entries = [
            entry
            for entry in history
            if (entry.top_class or entry.predicted_class or "__uncertain__") == class_id
        ]
        probabilities = [entry.probability for entry in entries if entry.probability is not None]
        rows.append(
            {
                "classe": class_labels.get(class_id, class_id),
                "análises": len(entries),
                "aceitas": sum(1 for entry in entries if entry.accepted),
                "baixa_confiança": sum(
                    1
                    for entry in entries
                    if entry.probability is not None and entry.probability < low_confidence_threshold
                ),
                "confiança_média": round(sum(probabilities) / len(probabilities), 3) if probabilities else None,
            }
        )
    return sorted(rows, key=lambda row: (-int(row["baixa_confiança"]), -int(row["análises"]), str(row["classe"])))


def correction_rows(
    feedback_entries: Iterable[RecognitionFeedback],
    class_labels: dict[str, str],
) -> list[dict[str, object]]:
    counter: Counter[tuple[str, str]] = Counter()
    examples: dict[tuple[str, str], RecognitionFeedback] = {}
    for feedback in feedback_entries:
        if not _feedback_has_mismatch(feedback):
            continue
        predicted = feedback.predicted_class or feedback.top_class or "__uncertain__"
        key = (predicted, feedback.expected_class)
        counter[key] += 1
        examples.setdefault(key, feedback)

    rows: list[dict[str, object]] = []
    for (predicted, expected), count in counter.most_common():
        example = examples[(predicted, expected)]
        rows.append(
            {
                "modelo_indicou": class_labels.get(predicted, predicted),
                "correto": class_labels.get(expected, expected),
                "ocorrências": count,
                "última_confiança": example.probability,
                "observação": example.note,
            }
        )
    return rows


def _feedback_has_mismatch(feedback: RecognitionFeedback) -> bool:
    predicted = feedback.predicted_class or feedback.top_class
    return bool(feedback.expected_class and predicted and feedback.expected_class != predicted)
