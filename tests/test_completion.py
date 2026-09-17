from __future__ import annotations

import unittest

from ecoscan.config import load_config
from ecoscan.services.completion import build_completion_plan, format_completion_markdown


class CompletionPlanTests(unittest.TestCase):
    def test_completion_plan_separates_demo_from_final_model(self) -> None:
        plan = build_completion_plan(load_config())

        self.assertGreaterEqual(plan.readiness_score, 0)
        self.assertGreater(len(plan.actions), 4)
        self.assertIn(plan.selected_model_kind, {"baseline", "visual_svm", "visual_knn", "transfer_learning", "none"})
        self.assertTrue(any(action.title == "Modelo final por transfer learning" for action in plan.actions))

    def test_completion_markdown_contains_final_reading(self) -> None:
        plan = build_completion_plan(load_config())
        markdown = format_completion_markdown(plan)

        self.assertIn("Checklist de conclusão", markdown)
        self.assertIn("Leitura correta", markdown)
        self.assertIn("Score de prontidão", markdown)


if __name__ == "__main__":
    unittest.main()
