from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ecoscan.disposal.targets import DisposalTarget
from ecoscan.services.recognition_safety import RecognitionSafetyDecision, capture_photo_tips


@dataclass(frozen=True)
class PublicNextAction:
    status: str
    tone: str
    title: str
    message: str
    material_label: str
    confidence_label: str
    destination_title: str
    destination_type: str
    bin_color_hex: str
    preparation_steps: tuple[str, ...]
    attention_note: str
    search_query: str | None
    can_search_collection: bool


def build_public_next_action(
    result: Any,
    target: DisposalTarget | None,
    safety_decision: RecognitionSafetyDecision,
) -> PublicNextAction:
    guidance = getattr(result, "guidance", None)
    material_label = (
        getattr(guidance, "display_name", "")
        or getattr(result, "predicted_class", None)
        or getattr(result, "top_class", None)
        or "resíduo não confirmado"
    )
    confidence_label = _confidence_label(getattr(result, "probability", None))

    if safety_decision.allow_disposal_guidance and target is not None and guidance is not None:
        return PublicNextAction(
            status=safety_decision.status,
            tone=safety_decision.tone,
            title="O que fazer agora",
            message=safety_decision.primary_action,
            material_label=str(material_label),
            confidence_label=confidence_label,
            destination_title=target.destination_title,
            destination_type=target.destination_type,
            bin_color_hex=target.bin_color_hex,
            preparation_steps=tuple(target.preparation_steps[:3]),
            attention_note=target.attention_note,
            search_query=target.search_query,
            can_search_collection=True,
        )

    return PublicNextAction(
        status=safety_decision.status,
        tone=safety_decision.tone,
        title="Antes de descartar",
        message=safety_decision.primary_action,
        material_label=str(material_label),
        confidence_label=confidence_label,
        destination_title="Destino não confirmado",
        destination_type="Tire outra foto ou corrija a classe antes de usar a orientação.",
        bin_color_hex="#d79f35",
        preparation_steps=capture_photo_tips()[:3],
        attention_note="Quando o sistema estiver incerto, a opção mais segura é refazer a foto ou registrar correção.",
        search_query=None,
        can_search_collection=False,
    )


def _confidence_label(value: float | None) -> str:
    if value is None:
        return "confiança indisponível"
    return f"{value * 100:.0f}% de confiança"
