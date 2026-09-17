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

    def test_allows_guidance_but_requests_confirmation_for_low_confidence(self) -> None:
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
        self.assertTrue(decision.allow_disposal_guidance)
        self.assertTrue(decision.encourage_feedback)

    def test_capture_tips_are_actionable(self) -> None:
        tips = capture_photo_tips()

        self.assertGreaterEqual(len(tips), 4)
        self.assertTrue(any("fundo" in tip for tip in tips))


if __name__ == "__main__":
    unittest.main()
