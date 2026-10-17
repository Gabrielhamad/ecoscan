from __future__ import annotations

import unittest
from types import SimpleNamespace

from ecoscan.services.recognition_safety import build_recognition_safety_decision, capture_photo_tips


class RecognitionSafetyTests(unittest.TestCase):
    def test_blocks_disposal_when_result_is_uncertain(self) -> None:
        result = SimpleNamespace(
            accepted=False,
            guidance=None,
            probability=0.41,
            reliability=None,
            material_rule=None,
            pipeline=SimpleNamespace(metadata={"capture_quality": {"status": "good"}}),
        )

        decision = build_recognition_safety_decision(result)

        self.assertEqual("uncertain", decision.status)
        self.assertFalse(decision.allow_disposal_guidance)
        self.assertTrue(decision.encourage_feedback)

    def test_blocks_automatic_guidance_for_low_confidence(self) -> None:
        result = SimpleNamespace(
            accepted=True,
            guidance=object(),
            probability=0.68,
            reliability=None,
            material_rule=None,
            pipeline=SimpleNamespace(metadata={"capture_quality": {"status": "good"}}),
        )

        decision = build_recognition_safety_decision(result, action_confidence_threshold=0.72)

        self.assertEqual("needs_confirmation", decision.status)
        self.assertFalse(decision.allow_disposal_guidance)
        self.assertTrue(decision.encourage_feedback)

    def test_invalid_scores_never_release_guidance(self) -> None:
        for score in (None, float("nan"), float("inf"), -0.1, 1.1, "invalid", True):
            with self.subTest(score=score):
                result = SimpleNamespace(accepted=True, guidance=object(), probability=score)
                self.assertFalse(build_recognition_safety_decision(result).allow_disposal_guidance)

    def test_visual_rule_cannot_bypass_confidence(self) -> None:
        result = SimpleNamespace(accepted=True, guidance=object(), probability=0.5, material_rule=object())
        self.assertFalse(build_recognition_safety_decision(result).allow_disposal_guidance)

    def test_insufficient_class_evidence_blocks_guidance_even_with_high_score(self) -> None:
        result = SimpleNamespace(accepted=True, guidance=object(), probability=0.99,
                                 reliability=SimpleNamespace(is_sufficient=False, message="Base insuficiente"))
        self.assertFalse(build_recognition_safety_decision(result).allow_disposal_guidance)

    def test_valid_supported_result_remains_available(self) -> None:
        result = SimpleNamespace(accepted=True, guidance=object(), probability=0.9,
                                 reliability=SimpleNamespace(is_sufficient=True))
        self.assertTrue(build_recognition_safety_decision(result).allow_disposal_guidance)

    def test_invalid_threshold_is_rejected(self) -> None:
        for threshold in (float("nan"), float("inf"), -1, 2):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                build_recognition_safety_decision(SimpleNamespace(), action_confidence_threshold=threshold)

    def test_capture_tips_are_actionable(self) -> None:
        tips = capture_photo_tips()

        self.assertGreaterEqual(len(tips), 4)
        self.assertTrue(any("fundo" in tip for tip in tips))


if __name__ == "__main__":
    unittest.main()
