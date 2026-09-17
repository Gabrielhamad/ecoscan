from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ecoscan.image_processing.quality import ImageQualityMetrics, analyze_image_quality
from ecoscan.segmentation.methods import (
    SegmentationResult,
    SegmentationUnavailableError,
    segment_image,
)


DEFAULT_CANDIDATE_METHODS = ("otsu", "hsv_color", "grabcut")


@dataclass(frozen=True)
class AdaptiveSegmentationResult:
    segmentation: SegmentationResult
    decision: dict[str, Any]


@dataclass(frozen=True)
class CandidateScore:
    name: str
    score: float
    foreground_ratio: float
    border_ratio: float
    significant_components: int
    largest_component_ratio: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": round(self.score, 4),
            "foreground_ratio": round(self.foreground_ratio, 5),
            "border_ratio": round(self.border_ratio, 5),
            "significant_components": self.significant_components,
            "largest_component_ratio": round(self.largest_component_ratio, 5),
            "reason": self.reason,
        }


def segment_image_adaptive(
    image: np.ndarray,
    parameters: dict[str, Any] | None = None,
    *,
    quality: ImageQualityMetrics | None = None,
) -> AdaptiveSegmentationResult:
    params = parameters or {}
    image_quality = quality or analyze_image_quality(image)
    candidate_methods = _candidate_methods(params)
    candidates: list[tuple[SegmentationResult, CandidateScore]] = []
    skipped: list[dict[str, str]] = []

    for method_name in candidate_methods:
        method_parameters = _method_parameters(params, method_name)
        try:
            result = segment_image(image, method_name, method_parameters)
        except SegmentationUnavailableError as exc:
            skipped.append({"name": method_name, "reason": str(exc)})
            continue

        score = _score_candidate(result, image_quality, params)
        candidates.append((result, score))

    if not candidates:
        result = segment_image(image, "otsu", _method_parameters(params, "otsu"))
        score = _score_candidate(result, image_quality, params)
        candidates.append((result, score))
        skipped.append({"name": "fallback", "reason": "nenhum candidato adaptativo estava disponível"})

    selected_result, selected_score = max(candidates, key=lambda item: item[1].score)
    decision = {
        "requested": "auto",
        "selected": selected_result.name,
        "reason": _selection_reason(selected_score, image_quality),
        "quality_profile": {
            "exposure": image_quality.exposure_status,
            "contrast": image_quality.contrast_status,
            "focus": image_quality.focus_status,
            "saturation_mean": image_quality.saturation_mean,
            "edge_density": image_quality.edge_density,
        },
        "candidates": [score.to_dict() for _, score in sorted(candidates, key=lambda item: item[1].score, reverse=True)],
        "skipped": skipped,
    }
    return AdaptiveSegmentationResult(segmentation=selected_result, decision=decision)


def _candidate_methods(params: dict[str, Any]) -> tuple[str, ...]:
    raw = params.get("candidate_methods") or params.get("methods") or DEFAULT_CANDIDATE_METHODS
    if isinstance(raw, str):
        return tuple(part.strip().lower() for part in raw.split(",") if part.strip())
    return tuple(str(method).strip().lower() for method in raw if str(method).strip())


def _method_parameters(params: dict[str, Any], method_name: str) -> dict[str, Any]:
    nested = params.get("method_parameters", {})
    method_parameters: dict[str, Any] = {}
    if isinstance(nested, dict) and isinstance(nested.get(method_name), dict):
        method_parameters.update(nested[method_name])
    if isinstance(params.get(method_name), dict):
        method_parameters.update(params[method_name])
    return method_parameters


def _score_candidate(
    result: SegmentationResult,
    quality: ImageQualityMetrics,
    params: dict[str, Any],
) -> CandidateScore:
    foreground_ratio = float(result.foreground_ratio)
    min_ratio = float(params.get("min_foreground_ratio", 0.025))
    max_ratio = float(params.get("max_foreground_ratio", 0.86))
    ideal_ratio = float(params.get("ideal_foreground_ratio", 0.38))
    border_ratio = _border_ratio(result.mask)
    component_stats = _component_stats(result.mask)

    ratio_score = 1.0 - min(abs(foreground_ratio - ideal_ratio) / max(ideal_ratio, 0.001), 1.0)
    border_score = 1.0 - min(border_ratio / 0.75, 1.0)
    component_score = _component_score(component_stats["significant_components"])
    largest_score = min(component_stats["largest_component_ratio"] / 0.28, 1.0)
    score = (
        ratio_score * 0.42
        + border_score * 0.22
        + component_score * 0.22
        + largest_score * 0.14
        + _method_prior(result.name, quality)
    )

    if foreground_ratio < min_ratio:
        score -= 0.75
    elif foreground_ratio > max_ratio:
        score -= 0.55

    reason = _candidate_reason(result.name, foreground_ratio, border_ratio, component_stats)
    return CandidateScore(
        name=result.name,
        score=score,
        foreground_ratio=foreground_ratio,
        border_ratio=border_ratio,
        significant_components=int(component_stats["significant_components"]),
        largest_component_ratio=float(component_stats["largest_component_ratio"]),
        reason=reason,
    )


def _border_ratio(mask: np.ndarray) -> float:
    binary = mask > 0
    if binary.size == 0:
        return 0.0
    border = np.concatenate(
        [
            binary[0, :],
            binary[-1, :],
            binary[1:-1, 0],
            binary[1:-1, -1],
        ]
    )
    return float(np.mean(border))


def _component_stats(mask: np.ndarray) -> dict[str, float | int]:
    binary = mask > 0
    height, width = binary.shape
    visited = np.zeros_like(binary, dtype=bool)
    total_pixels = max(1, height * width)
    min_area = max(12, int(total_pixels * 0.004))
    component_count = 0
    significant_components = 0
    largest_area = 0

    for start_y in range(height):
        for start_x in range(width):
            if not binary[start_y, start_x] or visited[start_y, start_x]:
                continue
            component_count += 1
            area = _flood_fill_area(binary, visited, start_x, start_y)
            largest_area = max(largest_area, area)
            if area >= min_area:
                significant_components += 1

    return {
        "component_count": component_count,
        "significant_components": significant_components,
        "largest_component_ratio": largest_area / total_pixels,
    }


def _flood_fill_area(binary: np.ndarray, visited: np.ndarray, start_x: int, start_y: int) -> int:
    height, width = binary.shape
    area = 0
    stack = [(start_x, start_y)]
    visited[start_y, start_x] = True
    while stack:
        x, y = stack.pop()
        area += 1
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if nx < 0 or ny < 0 or nx >= width or ny >= height:
                continue
            if binary[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                stack.append((nx, ny))
    return area


def _component_score(significant_components: int) -> float:
    if significant_components == 0:
        return 0.0
    if significant_components <= 4:
        return 1.0
    if significant_components <= 10:
        return 0.72
    return 0.35


def _method_prior(name: str, quality: ImageQualityMetrics) -> float:
    if name == "hsv_color":
        if quality.saturation_mean >= 0.18:
            return 0.16
        if quality.saturation_mean < 0.08:
            return -0.12
        return 0.02
    if name == "grabcut":
        score = 0.03
        if quality.edge_density >= 0.18:
            score += 0.08
        if quality.focus_status == "low":
            score -= 0.05
        return score
    if name == "otsu":
        score = 0.04
        if quality.contrast_status == "ok":
            score += 0.06
        if quality.saturation_mean < 0.10:
            score += 0.04
        return score
    return 0.0


def _candidate_reason(
    name: str,
    foreground_ratio: float,
    border_ratio: float,
    component_stats: dict[str, float | int],
) -> str:
    return (
        f"{name} gerou {foreground_ratio * 100:.1f}% de primeiro plano, "
        f"{int(component_stats['significant_components'])} componente(s) relevante(s) "
        f"e {border_ratio * 100:.1f}% de contato com a borda."
    )


def _selection_reason(score: CandidateScore, quality: ImageQualityMetrics) -> str:
    if score.name == "hsv_color":
        return "HSV foi escolhido por equilibrar cor, área segmentada e componentes relevantes."
    if score.name == "grabcut":
        return "GrabCut foi escolhido por lidar melhor com objeto central e fundo mais complexo."
    if quality.contrast_status == "ok":
        return "Otsu foi escolhido por apresentar separação global estável para esta imagem."
    return "Otsu foi escolhido como alternativa mais estável entre os métodos disponíveis."
