from __future__ import annotations

import unittest

from ecoscan.services.diagnostics import DatasetStatus
from ecoscan.services.field_testing import build_field_test_record
from ecoscan.services.history import HistoryEntry
from ecoscan.services.recognition_feedback import RecognitionFeedback
from ecoscan.services.recognition_improvement import (
    build_recognition_improvement_plan,
    confusion_table_rows,
    priority_table_rows,
)


class RecognitionImprovementTests(unittest.TestCase):
    def test_prioritizes_class_with_feedback_confusion_and_low_dataset(self) -> None:
        status = DatasetStatus(
            raw_counts={"metal": 12, "glass": 80, "plastic": 60},
            curated_counts={"metal": 5, "glass": 70, "plastic": 55},
            train_counts={},
            validation_counts={},
            test_counts={},
        )
        history = [
            _history("glass", "glass", 0.52, False),
            _history("metal", "metal", 0.66, True),
        ]
        feedback = [
            _feedback(expected="metal", predicted="glass", probability=0.52),
        ]

        plan = build_recognition_improvement_plan(
            history,
            feedback,
            status,
            {"metal": "Metal", "glass": "Vidro", "plastic": "Plástico"},
            classes=("metal", "glass", "plastic"),
            target_raw_per_class=50,
        )
        priority_rows = priority_table_rows(plan.priorities)
        confusion_rows = confusion_table_rows(plan.confusions)

        self.assertEqual("Metal", plan.priorities[0].label)
        self.assertIn(plan.priorities[0].priority, {"alta", "média"})
        self.assertIn("Coletar", plan.priorities[0].action)
        self.assertEqual("Vidro", confusion_rows[0]["modelo_indicou"])
        self.assertEqual("Metal", confusion_rows[0]["correto"])
        self.assertEqual("Metal", priority_rows[0]["classe"])

    def test_recommends_test_round_when_no_operational_data_exists(self) -> None:
        status = DatasetStatus(
            raw_counts={"metal": 0},
            curated_counts={"metal": 0},
            train_counts={},
            validation_counts={},
            test_counts={},
        )

        plan = build_recognition_improvement_plan(
            [],
            [],
            status,
            {"metal": "Metal"},
            classes=("metal",),
        )

        self.assertTrue(any("histórico" in recommendation for recommendation in plan.recommendations))
        self.assertEqual("Metal", plan.priorities[0].label)

    def test_field_tests_feed_priority_and_confusion_plan(self) -> None:
        status = DatasetStatus(
            raw_counts={"metal": 60, "glass": 60},
            curated_counts={"metal": 50, "glass": 50},
            train_counts={},
            validation_counts={},
            test_counts={},
        )
        field_tests = [
            build_field_test_record(
                tester_id="usuario_demo",
                tester_name="Cidadão",
                expected_class="metal",
                model_class="glass",
                result_status="errou",
                device_kind="celular",
                capture_mode="foto enviada",
                confidence=0.49,
                note="lata virou vidro",
            )
        ]

        plan = build_recognition_improvement_plan(
            [],
            [],
            status,
            {"metal": "Metal", "glass": "Vidro"},
            field_test_entries=field_tests,
            classes=("metal", "glass"),
        )
        priority_rows = priority_table_rows(plan.priorities)
        confusion_rows = confusion_table_rows(plan.confusions)

        self.assertEqual("Metal", plan.priorities[0].label)
        self.assertGreater(plan.priorities[0].field_wrong_count, 0)
        self.assertIn("campo", "; ".join(plan.priorities[0].reasons))
        self.assertEqual(1, priority_rows[0]["erros_campo"])
        self.assertEqual("Vidro", confusion_rows[0]["modelo_indicou"])
        self.assertEqual("Metal", confusion_rows[0]["correto"])


def _history(predicted: str, top: str, probability: float, accepted: bool) -> HistoryEntry:
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
        note="era lata de alumínio",
        image_path="reports/recognition_feedback/images/item.jpg",
    )


if __name__ == "__main__":
    unittest.main()
