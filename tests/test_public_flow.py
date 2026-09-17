from __future__ import annotations

import unittest
from types import SimpleNamespace

from ecoscan.disposal.targets import DisposalTarget
from ecoscan.services.public_flow import build_public_next_action
from ecoscan.services.recognition_safety import RecognitionSafetyDecision


class PublicFlowTests(unittest.TestCase):
    def test_builds_collection_action_when_guidance_is_safe(self) -> None:
        result = SimpleNamespace(
            guidance=SimpleNamespace(display_name="Lata de alumínio"),
            predicted_class="metal",
            top_class="metal",
            probability=0.91,
        )
        target = DisposalTarget(
            class_id="metal",
            destination_title="Coleta seletiva - metal",
            destination_type="Lixeira amarela ou ecoponto",
            bin_color_name="amarela",
            bin_color_hex="#d79f35",
            asset_path="assets/disposal_targets/metal.png",
            search_query="ecoponto coleta metal",
            preparation_steps=("Esvazie a lata.", "Amasse se possível.", "Leve limpa e seca."),
            attention_note="Não descarte com líquido dentro.",
        )
        decision = _decision(allow=True)

        action = build_public_next_action(result, target, decision)

        self.assertTrue(action.can_search_collection)
        self.assertEqual("Coleta seletiva - metal", action.destination_title)
        self.assertEqual("Lata de alumínio", action.material_label)
        self.assertEqual("91% de confiança", action.confidence_label)

    def test_blocks_collection_action_when_recognition_is_uncertain(self) -> None:
        result = SimpleNamespace(
            guidance=None,
            predicted_class=None,
            top_class="glass",
            probability=0.39,
        )
        decision = _decision(allow=False, tone="warn", status="uncertain")

        action = build_public_next_action(result, None, decision)

        self.assertFalse(action.can_search_collection)
        self.assertEqual("Destino não confirmado", action.destination_title)
        self.assertIn("outra foto", action.destination_type)
        self.assertEqual("39% de confiança", action.confidence_label)


def _decision(*, allow: bool, tone: str = "ok", status: str = "identified") -> RecognitionSafetyDecision:
    return RecognitionSafetyDecision(
        status=status,
        tone=tone,
        title="Identificado",
        message="Mensagem de teste.",
        primary_action="Ação recomendada.",
        allow_disposal_guidance=allow,
        encourage_feedback=not allow,
    )


if __name__ == "__main__":
    unittest.main()
