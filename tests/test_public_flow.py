from __future__ import annotations

import unittest
from types import SimpleNamespace

from ecoscan.config import PROJECT_ROOT
from ecoscan.disposal.targets import DisposalTarget, load_disposal_targets
from ecoscan.services.public_flow import build_public_next_action
from ecoscan.services.recognition_safety import RecognitionSafetyDecision


def _decision(*, allow: bool, tone: str = "ok", status: str = "identified") -> RecognitionSafetyDecision:
    return RecognitionSafetyDecision(
        status=status,
        tone=tone,
        title="Material sugerido",
        message="Mensagem de teste.",
        primary_action="Ação recomendada.",
        allow_disposal_guidance=allow,
        encourage_feedback=not allow,
    )


class PublicFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.targets = load_disposal_targets(PROJECT_ROOT / "config" / "disposal_targets.json")

    def test_confirmed_material_has_correct_bin_without_model_percentage(self) -> None:
        result = SimpleNamespace(
            guidance=SimpleNamespace(display_name="Metal"), predicted_class="metal",
            top_class="metal", probability=0.91,
        )
        action = build_public_next_action(result, self.targets["metal"], _decision(allow=True))
        self.assertTrue(action.can_search_collection)
        self.assertEqual("Lixeira amarela", action.destination_title)
        self.assertEqual("Metal", action.material_label)
        self.assertFalse(hasattr(action, "confidence_label"))

    def test_unconfirmed_material_previews_destination_without_authorizing_disposal(self) -> None:
        result = SimpleNamespace(
            guidance=None, predicted_class=None, top_class="glass", probability=0.39,
        )
        action = build_public_next_action(
            result, self.targets["glass"],
            _decision(allow=False, tone="warn", status="needs_confirmation"),
            suggested_material_label="Vidro",
        )
        self.assertFalse(action.can_search_collection)
        self.assertEqual("Lixeira verde", action.destination_title)
        self.assertEqual("Vidro", action.material_label)
        self.assertEqual((), action.preparation_steps)
        self.assertNotIn("39", str(action))
        self.assertFalse(hasattr(action, "confidence_label"))

    def test_unknown_or_bad_photo_has_no_automatic_destination(self) -> None:
        result = SimpleNamespace(guidance=None, top_class="metal", probability=0.99)
        for status in ("retake", "outside_scope", "uncertain", "needs_training"):
            with self.subTest(status=status):
                action = build_public_next_action(
                    result, self.targets["metal"],
                    _decision(allow=False, tone="warn", status=status),
                )
                self.assertFalse(action.can_search_collection)
                self.assertEqual("Selecione o material", action.destination_title)

    def test_never_exposes_invalid_or_extreme_scores(self) -> None:
        values = (None, 0.0, 0.25, 0.95, 1.0, float("nan"), "invalid")
        for value in values:
            with self.subTest(value=value):
                action = build_public_next_action(
                    SimpleNamespace(probability=value), None, _decision(allow=False),
                )
                self.assertNotIn("pontuação", str(action).lower())
                self.assertNotIn("confiança", str(action).lower())
                self.assertNotIn("%", str(action))

    def test_special_materials_require_collection_points_not_recycling_bin(self) -> None:
        for class_id in ("battery", "electronic"):
            with self.subTest(class_id=class_id):
                action = build_public_next_action(
                    SimpleNamespace(top_class=class_id),
                    self.targets[class_id],
                    _decision(allow=False, tone="warn", status="needs_confirmation"),
                )
                self.assertIn("Ponto", action.destination_title)
                self.assertFalse(action.can_search_collection)


if __name__ == "__main__":
    unittest.main()
