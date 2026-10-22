from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


@dataclass(frozen=True)
class RecognitionSafetyDecision:
    status: str
    tone: str
    title: str
    message: str
    primary_action: str
    allow_disposal_guidance: bool
    encourage_feedback: bool


def build_recognition_safety_decision(
    result: Any,
    *,
    action_confidence_threshold: float = 0.72,
) -> RecognitionSafetyDecision:
    capture_status = _capture_status(result)
    probability = getattr(result, "probability", None)
    accepted = bool(getattr(result, "accepted", False))
    has_guidance = getattr(result, "guidance", None) is not None
    reliability = getattr(result, "reliability", None)
    if not math.isfinite(action_confidence_threshold) or not 0 <= action_confidence_threshold <= 1:
        raise ValueError("action_confidence_threshold must be finite and between 0 and 1")
    try:
        valid_score = probability is not None and not isinstance(probability, bool) and math.isfinite(float(probability)) and 0 <= float(probability) <= 1
    except (TypeError, ValueError, OverflowError):
        valid_score = False

    if getattr(result, "outside_scope", False):
        return RecognitionSafetyDecision(
            status="outside_scope", tone="warn", title="Item fora do escopo ou não confirmado",
            message="Este piloto não identifica alimentos ou resíduos orgânicos.",
            primary_action="Confira os itens aceitos e reporte o resultado para revisão.",
            allow_disposal_guidance=False, encourage_feedback=True,
        )

    if not getattr(result, "processing_compatible", True):
        return RecognitionSafetyDecision(
            status="needs_training", tone="warn", title="Confirme o material",
            message="A preparação de imagem foi atualizada; o modelo ainda precisa ser treinado e validado com ela.",
            primary_action="Consulte Descarte para escolher o material ou envie uma correção para revisão.",
            allow_disposal_guidance=False, encourage_feedback=True,
        )

    if capture_status == "retake":
        return RecognitionSafetyDecision(
            status="retake",
            tone="danger",
            title="Refaça a foto para evitar orientação errada",
            message="A imagem não tem qualidade suficiente para orientar descarte com segurança.",
            primary_action="Tirar nova foto com mais luz, foco e objeto centralizado.",
            allow_disposal_guidance=False,
            encourage_feedback=False,
        )

    if getattr(result, "model_type", "") == "semantic_onnx_preview":
        return RecognitionSafetyDecision(
            status="needs_confirmation", tone="warn", title="Confirme o material sugerido",
            message="O novo reconhecedor está em avaliação. A hipótese não confirma o material do objeto.",
            primary_action="Confira a hipótese, escolha o material em Descarte ou envie uma correção à secretaria.",
            allow_disposal_guidance=False, encourage_feedback=True,
        )

    if not accepted or not has_guidance or not valid_score:
        return RecognitionSafetyDecision(
            status="uncertain",
            tone="warn",
            title="Não identificado com segurança",
            message="O sistema ainda não tem confiança suficiente para indicar um destino como certo.",
            primary_action="Envie outra foto com fundo simples ou corrija a classe para melhorar o dataset.",
            allow_disposal_guidance=False,
            encourage_feedback=True,
        )

    if reliability is not None and not getattr(reliability, "is_sufficient", True):
        return RecognitionSafetyDecision(
            status="needs_confirmation",
            tone="warn",
            title="Classe provável, mas precisa de confirmação",
            message=str(getattr(reliability, "message", "") or "A base desta classe ainda precisa de reforço."),
            primary_action="Confira o material antes de descartar e envie correção se estiver errado.",
            allow_disposal_guidance=False,
            encourage_feedback=True,
        )

    if float(probability) < action_confidence_threshold:
        return RecognitionSafetyDecision(
            status="needs_confirmation",
            tone="warn",
            title="Resultado provável",
            message="A análise encontrou uma classe provável, mas a confiança ainda não é alta.",
            primary_action="Escolha o material na aba Descarte ou envie a imagem para revisão da secretaria.",
            allow_disposal_guidance=False,
            encourage_feedback=True,
        )

    return RecognitionSafetyDecision(
        status="identified",
        tone="ok",
        title="Material sugerido pela análise",
        message="A análise passou pelos critérios do piloto, mas não confirma composição, conteúdo ou contaminação.",
        primary_action="Confirme o material antes de seguir o preparo e consultar a coleta.",
        allow_disposal_guidance=True,
        encourage_feedback=False,
    )


def capture_photo_tips() -> tuple[str, ...]:
    return (
        "fotografe um resíduo principal por vez;",
        "use fundo simples e boa iluminação;",
        "deixe o objeto inteiro visível, incluindo topo, base ou tampa;",
        "evite reflexos fortes em vidro, metal e plástico transparente;",
        "se houver dúvida, tire outra foto em ângulo diferente.",
    )


def _capture_status(result: Any) -> str:
    metadata = getattr(getattr(result, "pipeline", None), "metadata", {})
    if not isinstance(metadata, dict):
        return ""
    capture_quality = metadata.get("capture_quality") or {}
    if not isinstance(capture_quality, dict):
        return ""
    return str(capture_quality.get("status") or "").strip().lower()
