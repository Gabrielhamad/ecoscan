from __future__ import annotations

import unittest

from ecoscan.config import load_config
from ecoscan.services.diagnostics import model_status
from ecoscan.services.field_testing import build_field_test_record
from ecoscan.services.model_governance import (
    build_hard_cases,
    build_model_governance_plan,
    hard_case_table_rows,
    metric_snapshot_rows,
    model_gate_table_rows,
    read_evaluation_snapshots,
)
from ecoscan.services.recognition_feedback import RecognitionFeedback


class ModelGovernanceTests(unittest.TestCase):
    def test_builds_governance_plan_from_metrics_and_real_errors(self) -> None:
        config = load_config()
        feedback = [
            _feedback(expected="metal", predicted="glass", probability=0.58),
        ]
        field_tests = [
            build_field_test_record(
                tester_id="colega_1",
                tester_name="Colega",
                expected_class="plastic",
                model_class="paper_cardboard",
                result_status="errou",
                device_kind="celular",
                capture_mode="camera",
                confidence=0.42,
                note="garrafa virou papel",
            )
        ]

        plan = build_model_governance_plan(
            config,
            feedback_entries=feedback,
            field_test_entries=field_tests,
            class_labels={"metal": "Metal", "glass": "Vidro", "plastic": "Plástico", "paper_cardboard": "Papel"},
        )
        gate_rows = model_gate_table_rows(plan.gates)
        case_rows = hard_case_table_rows(
            plan.hard_cases,
            {"metal": "Metal", "glass": "Vidro", "plastic": "Plástico", "paper_cardboard": "Papel"},
        )

        self.assertGreaterEqual(plan.evaluation_count, 1)
        self.assertTrue(any(row["critério"] == "Regra de promoção segura" for row in gate_rows))
        self.assertEqual(2, len(plan.hard_cases))
        self.assertEqual("Metal", case_rows[1]["esperado"])
        self.assertTrue(any("macro-F1" in item for item in plan.recommendations))

        if not model_status(config).final_model_exists:
            self.assertEqual("prepared", plan.promotion_status)

    def test_reads_metric_snapshots_and_exposes_reference_row(self) -> None:
        plan = build_model_governance_plan(load_config())
        snapshots = read_evaluation_snapshots(load_config())
        rows = metric_snapshot_rows(plan)

        self.assertGreaterEqual(len(snapshots), 1)
        self.assertTrue(rows)
        self.assertIn("macro_f1", rows[0])

    def test_hard_cases_ignore_correct_predictions(self) -> None:
        records = [
            build_field_test_record(
                tester_id="u",
                tester_name="Usuário",
                expected_class="metal",
                model_class="metal",
                result_status="acertou",
                device_kind="celular",
                capture_mode="upload",
            )
        ]

        self.assertEqual((), build_hard_cases([], records, {"metal": "Metal"}))


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
        note="classe corrigida durante o teste",
        image_path="reports/recognition_feedback/images/item.jpg",
    )


if __name__ == "__main__":
    unittest.main()
