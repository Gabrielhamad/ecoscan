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

    A service-approved suggestion may preview its category destination.
    Only a manually confirmed category unlocks complete instructions elsewhere.
    """
    # Recognition provides category language; only explicit human selection opens
    # complete instructions in the UI, including after a valid identified decision.
    suggestion = safety_decision.suggested_class
    has_suggestion = safety_decision.status in {"probable", "identified"} and suggestion is not None
    material_label = str(suggested_material_label or suggestion) if has_suggestion else "Material a confirmar"

    if has_suggestion and target is not None and target.class_id == suggestion:
        return PublicNextAction(
            status=safety_decision.status,
            tone=safety_decision.tone,
            title="Destino após confirmar o material",
            message="Confirme ou corrija o material antes de seguir a orientação.",
            material_label=material_label,
            destination_title=target.destination_title,
            destination_type=target.destination_type,
            bin_color_hex=target.bin_color_hex,
            preparation_steps=(),
            attention_note="O destino corresponde à categoria visual; a foto não confirma composição, limpeza ou conteúdo.",
            search_query=None,
            can_search_collection=False,
        )

    return PublicNextAction(
        status=safety_decision.status,
        tone=safety_decision.tone,
        title="Como continuar",
        message=safety_decision.primary_action,
        material_label=material_label,
        destination_title="Selecione o material",
        destination_type="Escolha a categoria que você reconhece para consultar o descarte.",
        bin_color_hex="#d79f35",
        preparation_steps=(() if safety_decision.status == "model_unavailable" else capture_photo_tips()[:3]),
        attention_note=safety_decision.message,
        search_query=None,
        can_search_collection=False,
    )
