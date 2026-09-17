from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ecoscan.image_processing.quality import ImageQualityMetrics
from ecoscan.segmentation.elements import ElementAnalysis


@dataclass(frozen=True)
class CaptureQualityAssessment:
    status: str
    score: int
    title: str
    message: str
    reasons: tuple[str, ...]
    actions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_capture_quality(
    before_filter: ImageQualityMetrics,
    after_filter: ImageQualityMetrics,
    element_analysis: ElementAnalysis,
) -> CaptureQualityAssessment:
    score = 100
    reasons: list[str] = []
    actions: list[str] = []

    if after_filter.exposure_status == "underexposed":
        score -= 24
        reasons.append("imagem ainda está escura após o tratamento")
        actions.append("Aumente a iluminação ou aproxime o resíduo de uma fonte de luz difusa.")
    elif after_filter.exposure_status == "overexposed":
        score -= 24
        reasons.append("imagem ainda está clara demais após o tratamento")
        actions.append("Reduza reflexos diretos e evite apontar a câmera contra luz forte.")
    elif before_filter.exposure_status != "ok":
        score -= 8
        reasons.append("exposição foi corrigida, mas a captura original estava fora do ideal")

    if after_filter.contrast_status == "low":
        score -= 18
        reasons.append("contraste entre resíduo e fundo ainda está baixo")
        actions.append("Use um fundo liso que contraste com a cor do resíduo.")
    elif before_filter.contrast_status == "low":
        score -= 6
        reasons.append("contraste original era baixo e exigiu correção automática")

    if after_filter.focus_status == "low":
        score -= 24
        reasons.append("nitidez baixa; filtro não recupera detalhe perdido")
        actions.append("Segure a câmera firme, toque para focar e capture a imagem novamente.")

    if after_filter.edge_density > 0.42:
        score -= 12
        reasons.append("há muitas bordas ou textura de fundo competindo com o resíduo")
        actions.append("Remova objetos próximos e fotografe apenas o resíduo principal.")

    if element_analysis.significant_count == 0:
        score -= 25
        reasons.append("a segmentação não encontrou um elemento visual significativo")
        actions.append("Centralize o resíduo e deixe ele ocupar uma parte clara da imagem.")
    elif element_analysis.largest_area_ratio < 0.035:
        score -= 16
        reasons.append("o resíduo parece pequeno demais no enquadramento")
        actions.append("Aproxime a câmera até o resíduo ocupar mais espaço sem cortar as bordas.")
    elif element_analysis.foreground_ratio > 0.88:
        score -= 14
        reasons.append("o objeto ou fundo ocupa quase toda a máscara")
        actions.append("Afaste um pouco a câmera e deixe uma margem visível ao redor do resíduo.")

    if element_analysis.likely_multi_object:
        score -= 10
        reasons.append("há múltiplos elementos relevantes na cena")
        actions.append("Analise um resíduo por vez para obter orientação de descarte mais confiável.")

    normalized_score = max(0, min(100, int(round(score))))
    unique_actions = _unique(actions)
    if not unique_actions and normalized_score < 90:
        unique_actions = ("Capture em fundo simples, com boa luz e o resíduo centralizado.",)

    force_retake = after_filter.focus_status == "low" or element_analysis.significant_count == 0
    if normalized_score < 55 or force_retake:
        retake_score = min(normalized_score, 54) if force_retake else normalized_score
        return CaptureQualityAssessment(
            status="retake",
            score=retake_score,
            title="Nova captura recomendada",
            message="A imagem ainda não oferece condição técnica adequada para uma leitura confiável.",
            reasons=tuple(reasons),
            actions=unique_actions,
        )
    if normalized_score < 82 or reasons:
        return CaptureQualityAssessment(
            status="attention",
            score=normalized_score,
            title="Captura utilizável com ajustes",
            message="O sistema conseguiu processar a imagem, mas a qualidade pode afetar a confiança.",
            reasons=tuple(reasons),
            actions=unique_actions,
        )
    return CaptureQualityAssessment(
        status="good",
        score=normalized_score,
        title="Captura adequada",
        message="A imagem está em boas condições para segmentação e reconhecimento.",
        reasons=("exposição, contraste e enquadramento estão dentro do esperado",),
        actions=("Mantenha esse padrão para novas fotos da base de imagens.",),
    )


def _unique(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        result.append(value)
        seen.add(value)
    return tuple(result)
