from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ecoscan.image_processing.filters import FilterResult, FilterUnavailableError, apply_filter
from ecoscan.image_processing.image_io import ensure_uint8
from ecoscan.image_processing.quality import ImageQualityMetrics, analyze_image_quality


ENHANCEMENT_FILTERS = frozenset({"none", "gaussian", "median", "bilateral", "clahe"})
DEFAULT_CANDIDATE_SEQUENCES: tuple[tuple[str, ...], ...] = (
    ("none",),
    ("gaussian",),
    ("median",),
    ("bilateral",),
    ("clahe",),
    ("clahe", "gaussian"),
    ("clahe", "median"),
    ("clahe", "bilateral"),
)


@dataclass(frozen=True)
class AdaptiveFilterPipelineResult:
    filter_result: FilterResult
    decision: dict[str, Any]


@dataclass(frozen=True)
class _CandidateEvaluation:
    sequence: tuple[str, ...]
    result: FilterResult
    metrics: ImageQualityMetrics
    score: float
    row: dict[str, Any]


def apply_adaptive_filter_pipeline(
    image: np.ndarray,
    filters_config: dict[str, Any] | None = None,
    *,
    quality: ImageQualityMetrics | None = None,
    overrides: dict[str, Any] | None = None,
) -> AdaptiveFilterPipelineResult:
    """Evaluate short enhancement pipelines and return the best preprocessing result."""

    source = ensure_uint8(image)
    before = quality or analyze_image_quality(source)
    config = dict(filters_config or {})
    auto_config = dict(config.get("auto", {}))
    auto_config.update(overrides or {})
    method_parameters = _method_parameters(config, auto_config)
    sequences = _candidate_sequences(before, auto_config)

    evaluations: list[_CandidateEvaluation] = []
    skipped: list[dict[str, str]] = []
    for sequence in sequences:
        try:
            candidate = _evaluate_sequence(source, sequence, method_parameters, before)
            evaluations.append(candidate)
        except FilterUnavailableError as exc:
            skipped.append({"sequence": _format_sequence(sequence), "reason": str(exc)})
        except ValueError as exc:
            skipped.append({"sequence": _format_sequence(sequence), "reason": str(exc)})

    if not evaluations:
        fallback = _evaluate_sequence(source, ("none",), method_parameters, before)
        evaluations.append(fallback)

    selected = max(evaluations, key=lambda item: item.score)
    issues = _quality_issues(before)
    reason = _decision_reason(issues, selected.sequence)
    rows = sorted((item.row for item in evaluations), key=lambda row: row["score"], reverse=True)

    decision = {
        "requested": "auto",
        "mode": "adaptive_filter_pipeline",
        "selected": _format_sequence(selected.sequence),
        "selected_sequence": list(selected.sequence),
        "reason": reason,
        "quality_issues": issues or ["imagem adequada para preparação leve"],
        "candidates": rows,
        "skipped": skipped,
    }
    return AdaptiveFilterPipelineResult(
        filter_result=_compose_pipeline_result(selected, reason),
        decision=decision,
    )


def _method_parameters(config: dict[str, Any], auto_config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    configured = dict(auto_config.get("method_parameters", {}))
    parameters: dict[str, dict[str, Any]] = {}
    for filter_name in ENHANCEMENT_FILTERS:
        method_config = dict(config.get(filter_name, {}))
        method_config.update(dict(configured.get(filter_name, {})))
        parameters[filter_name] = method_config
    return parameters


def _candidate_sequences(
    metrics: ImageQualityMetrics,
    auto_config: dict[str, Any],
) -> list[tuple[str, ...]]:
    requested = auto_config.get("candidate_sequences") or DEFAULT_CANDIDATE_SEQUENCES
    max_steps = int(auto_config.get("max_steps", 2))
    profile_sequences = _profile_sequences(metrics)
    normalized = [_normalize_sequence(sequence) for sequence in requested]

    sequences: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    for sequence in [*profile_sequences, *normalized, *DEFAULT_CANDIDATE_SEQUENCES]:
        if not sequence or sequence in seen:
            continue
        active_steps = [name for name in sequence if name != "none"]
        if len(active_steps) > max_steps:
            continue
        if any(name not in ENHANCEMENT_FILTERS for name in sequence):
            continue
        if "none" in sequence and len(sequence) > 1:
            continue
        sequences.append(sequence)
        seen.add(sequence)
    return sequences


def _profile_sequences(metrics: ImageQualityMetrics) -> list[tuple[str, ...]]:
    sequences: list[tuple[str, ...]] = []
    needs_contrast = metrics.exposure_status != "ok" or metrics.contrast_status == "low"
    noisy_or_complex = metrics.edge_density > 0.35

    if needs_contrast:
        sequences.extend(
            [
                ("clahe",),
                ("clahe", "median"),
                ("clahe", "gaussian"),
                ("clahe", "bilateral"),
            ]
        )
    if noisy_or_complex:
        sequences.extend([("median",), ("bilateral",), ("gaussian",)])
    if metrics.focus_status == "low":
        sequences.extend([("none",), ("clahe",)])
    if not needs_contrast and not noisy_or_complex:
        sequences.extend([("gaussian",), ("bilateral",), ("none",)])
    return sequences


def _normalize_sequence(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        raw_parts = value.replace("->", ",").replace("+", ",").split(",")
    else:
        raw_parts = list(value)
    return tuple(str(part).strip().lower() for part in raw_parts if str(part).strip())


def _evaluate_sequence(
    image: np.ndarray,
    sequence: tuple[str, ...],
    method_parameters: dict[str, dict[str, Any]],
    before: ImageQualityMetrics,
) -> _CandidateEvaluation:
    current = ensure_uint8(image)
    steps: list[FilterResult] = []
    for filter_name in sequence:
        parameters = dict(method_parameters.get(filter_name, {}))
        step = apply_filter(current, filter_name, parameters)
        steps.append(step)
        current = step.image

    metrics = analyze_image_quality(current)
    score = _score_candidate(before, metrics, sequence)
    result = _sequence_result(sequence, current, steps, metrics, score)
    return _CandidateEvaluation(
        sequence=sequence,
        result=result,
        metrics=metrics,
        score=score,
        row={
            "sequence": _format_sequence(sequence),
            "score": round(score, 2),
            "contrast": metrics.contrast,
            "edge_density": metrics.edge_density,
            "sharpness": metrics.sharpness,
            "exposure": metrics.exposure_status,
            "focus": metrics.focus_status,
        },
    )


def _score_candidate(
    before: ImageQualityMetrics,
    after: ImageQualityMetrics,
    sequence: tuple[str, ...],
) -> float:
    score = 0.0

    score += 20.0 if after.exposure_status == "ok" else 7.0
    if before.exposure_status != "ok" and after.exposure_status == "ok":
        score += 6.0

    score += min(after.contrast / 0.30, 1.0) * 28.0
    if before.contrast_status == "low" and after.contrast > before.contrast:
        score += min((after.contrast - before.contrast) / 0.10, 1.0) * 6.0

    if 0.05 <= after.edge_density <= 0.30:
        score += 20.0
    elif after.edge_density < 0.05:
        score += 11.0
    elif after.edge_density <= 0.42:
        score += 13.0
    else:
        score += 5.0
    if before.edge_density > 0.35 and after.edge_density < before.edge_density:
        score += min((before.edge_density - after.edge_density) / 0.18, 1.0) * 7.0

    score += min(after.sharpness / 0.010, 1.0) * 14.0
    if before.focus_status == "ok" and after.sharpness < before.sharpness * 0.65:
        score -= 7.0
    if after.focus_status == "low":
        score -= 4.0

    score += min(after.saturation_mean / 0.22, 1.0) * 5.0
    if before.saturation_mean > 0.10 and after.saturation_mean < before.saturation_mean * 0.70:
        score -= 4.0

    needs_contrast = before.exposure_status != "ok" or before.contrast_status == "low"
    noisy_or_complex = before.edge_density > 0.35
    if needs_contrast and "clahe" in sequence:
        score += 7.0
    if noisy_or_complex and any(name in sequence for name in ("median", "bilateral", "gaussian")):
        score += 5.0
    if not needs_contrast and not noisy_or_complex and sequence in {("gaussian",), ("bilateral",)}:
        score += 3.0

    active_steps = [name for name in sequence if name != "none"]
    score -= max(0, len(active_steps) - 1) * 1.5
    return score


def _sequence_result(
    sequence: tuple[str, ...],
    image: np.ndarray,
    steps: list[FilterResult],
    metrics: ImageQualityMetrics,
    score: float,
) -> FilterResult:
    return FilterResult(
        name=f"auto -> {_format_sequence(sequence)}",
        image=ensure_uint8(image),
        parameters={
            "sequence": list(sequence),
            "steps": [
                {
                    "name": step.name,
                    "parameters": step.parameters,
                    "dependency": step.dependency,
                }
                for step in steps
            ],
            "score": round(score, 2),
            "quality_after": metrics.to_dict(),
        },
        explanation="Pipeline adaptativo avaliado por métricas de contraste, exposição, bordas, nitidez e cor.",
        dependency=_combine_dependencies(steps),
    )


def _compose_pipeline_result(candidate: _CandidateEvaluation, reason: str) -> FilterResult:
    result = candidate.result
    return FilterResult(
        name=result.name,
        image=result.image,
        parameters=result.parameters,
        explanation=f"{result.explanation} {reason}",
        dependency=result.dependency,
    )


def _combine_dependencies(steps: list[FilterResult]) -> str:
    dependencies: list[str] = []
    for step in steps:
        if step.dependency not in dependencies:
            dependencies.append(step.dependency)
    return " + ".join(dependencies) if dependencies else "numpy"


def _quality_issues(metrics: ImageQualityMetrics) -> list[str]:
    issues: list[str] = []
    if metrics.exposure_status == "underexposed":
        issues.append("exposição baixa")
    elif metrics.exposure_status == "overexposed":
        issues.append("exposição alta")
    if metrics.contrast_status == "low":
        issues.append("baixo contraste")
    if metrics.edge_density > 0.35:
        issues.append("excesso de bordas ou fundo complexo")
    if metrics.focus_status == "low":
        issues.append("baixa nitidez")
    return issues


def _decision_reason(issues: list[str], sequence: tuple[str, ...]) -> str:
    selected = _format_sequence(sequence)
    if issues:
        return (
            f"Foram detectados {', '.join(issues)}. "
            f"A sequência {selected} teve o melhor equilíbrio entre melhoria visual e preservação do objeto."
        )
    return (
        f"A imagem está em condição adequada. A sequência {selected} mantém uma preparação leve "
        "antes da segmentação e do reconhecimento."
    )


def _format_sequence(sequence: tuple[str, ...]) -> str:
    return " -> ".join(sequence)
