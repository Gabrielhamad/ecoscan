from __future__ import annotations

import unittest

from ecoscan.services.history import HistoryEntry
from ecoscan.services.recognition_feedback import RecognitionFeedback
from ecoscan.services.usage_quality import (
    build_recognition_quality_summary,
    class_quality_rows,
    correction_rows,
)


class UsageQualityTests(unittest.TestCase):
    def test_quality_summary_counts_uncertain_and_corrections(self) -> None:
        history = [
            _history("metal", "metal", 0.82, True),
            _history(None, "glass", 0.48, False),
        ]
        feedback = [
            _feedback(expected="metal", predicted="glass", probability=0.48),
        ]

        summary = build_recognition_quality_summary(history, feedback, low_confidence_threshold=0.72)
        correction_table = correction_rows(feedback, {"metal": "Metal", "glass": "Vidro"})
        quality_table = class_quality_rows(history, {"metal": "Metal", "glass": "Vidro"})

        self.assertEqual(2, summary.analysis_count)
        self.assertEqual(1, summary.accepted_count)
        self.assertEqual(1, summary.uncertain_count)
        self.assertEqual(1, summary.low_confidence_count)
        self.assertEqual(1, summary.correction_pair_count)
        self.assertEqual("Vidro", correction_table[0]["modelo_indicou"])
        self.assertEqual("Metal", correction_table[0]["correto"])
        self.assertEqual("Vidro", quality_table[0]["classe"])


def _history(predicted: str | None, top: str | None, probability: float, accepted: bool) -> HistoryEntry:
    return HistoryEntry(
        id="h",
        timestamp_utc="2026-01-01T00:00:00+00:00",
        source_path=None,
        predicted_class=predicted,
        top_class=top,
        probability=probability,
        accepted=accepted,
        model_type="visual_knn",
        filter_name="auto",
        segmentation_name="auto",
        environmental_category=None,
        guidance_summary=None,
    )


def _feedback(expected: str, predicted: str, probability: float) -> RecognitionFeedback:
    return RecognitionFeedback(
        id="f",
        timestamp_utc="2026-01-01T00:00:00+00:00",
        reporter_id="usuario_demo",
        reporter_name="Usuário",
        expected_class=expected,
        predicted_class=predicted,
        top_class=predicted,
        probability=probability,
        accepted=True,
        model_type="visual_knn",
        filter_name="auto",
        segmentation_name="auto",
        source_kind="upload",
        note="era metal",
        image_path="reports/recognition_feedback/images/item.jpg",
    )


if __name__ == "__main__":
    unittest.main()
