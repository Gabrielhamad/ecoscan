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
    *,
    suggested_material_label: str | None = None,
) -> PublicNextAction:
    """Show category-specific destinations without exposing model confidence.

    An unconfirmed classification may preview the appropriate bin for that
    material, but only a verified/user-confirmed category unlocks instructions.
    """
    guidance = getattr(result, "guidance", None)
    material_label = (
        suggested_material_label
        or getattr(guidance, "display_name", "")
        or getattr(result, "predicted_class", None)
        or getattr(result, "top_class", None)
        or "Material a confirmar"
    )

    if safety_decision.allow_disposal_guidance and target is not None and guidance is not None:
        return PublicNextAction(
            status=safety_decision.status,
            tone=safety_decision.tone,
            title="Destino do material",
            message=safety_decision.primary_action,
            material_label=str(material_label),
            destination_title=target.destination_title,
            destination_type=target.destination_type,
            bin_color_hex=target.bin_color_hex,
            preparation_steps=tuple(target.preparation_steps[:3]),
            attention_note=target.attention_note,
            search_query=target.search_query,
            can_search_collection=True,
        )

    if safety_decision.status == "needs_confirmation" and target is not None:
        return PublicNextAction(
            status=safety_decision.status,
            tone=safety_decision.tone,
            title="Destino para o material sugerido",
            message="Confira o material da foto antes de seguir a orientação.",
            material_label=str(material_label),
            destination_title=target.destination_title,
            destination_type=target.destination_type,
            bin_color_hex=target.bin_color_hex,
            preparation_steps=(),
            attention_note="Este destino corresponde à categoria exibida, não é uma confirmação da composição pela foto.",
            search_query=None,
            can_search_collection=False,
        )

    return PublicNextAction(
        status=safety_decision.status,
        tone=safety_decision.tone,
        title="Como continuar",
        message=safety_decision.primary_action,
        material_label=str(material_label),
        destination_title="Selecione o material",
        destination_type="Escolha a categoria que você reconhece para consultar o descarte.",
        bin_color_hex="#d79f35",
        preparation_steps=(() if safety_decision.status == "needs_training" else capture_photo_tips()[:3]),
        attention_note=safety_decision.message,
        search_query=None,
        can_search_collection=False,
    )
