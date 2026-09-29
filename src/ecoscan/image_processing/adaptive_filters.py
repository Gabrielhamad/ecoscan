"""Conservative corrections with an unchanged-image control and measurable gates."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from ecoscan.image_processing.filters import FilterResult, FilterUnavailableError, apply_filter
from ecoscan.image_processing.image_io import ensure_uint8
from ecoscan.image_processing.preprocessing import to_grayscale
from ecoscan.image_processing.quality import ImageQualityMetrics


ENHANCEMENT_FILTERS = frozenset({"none", "gaussian", "median", "bilateral", "clahe"})


@dataclass(frozen=True)
class AdaptiveFilterPipelineResult:
    filter_result: FilterResult
    decision: dict[str, Any]


def _impulse_mask(image: np.ndarray) -> np.ndarray:
    import cv2
    gray = to_grayscale(image)
    median = cv2.medianBlur(gray, 3)
    extreme = (gray <= 3) | (gray >= 252)
    extreme_neighbors = cv2.boxFilter(extreme.astype(np.float32), -1, (3, 3), normalize=False)
    return extreme & (np.abs(gray.astype(float) - median) > 45) & (extreme_neighbors <= 2)


def correction_diagnostics(image: np.ndarray) -> dict[str, float]:
    from skimage.restoration import estimate_sigma

    gray = to_grayscale(ensure_uint8(image))
    impulse = _impulse_mask(image)
    sigma = float(estimate_sigma(gray.astype(float) / 255.0, channel_axis=None)) * 255.0
    low, high = np.percentile(gray, [5, 95])
    return {
        "noise_sigma": round(sigma if np.isfinite(sigma) else 0.0, 4),
        "impulse_ratio": float(impulse.mean()),
        "robust_range": float(high - low),
        "clipped_ratio": float(((gray <= 2) | (gray >= 253)).mean()),
    }


def _preservation(before: np.ndarray, after: np.ndarray) -> dict[str, float]:
    import cv2
    from skimage.metrics import structural_similarity

    a, b = before.astype(float), after.astype(float)
    lab_a = cv2.cvtColor(before, cv2.COLOR_RGB2LAB).astype(float)
    lab_b = cv2.cvtColor(after, cv2.COLOR_RGB2LAB).astype(float)
    # Compare scene edges at a modest scale so random noise does not count as detail.
    gray_a = cv2.GaussianBlur(to_grayscale(before), (5, 5), 1.0).astype(float)
    gray_b = cv2.GaussianBlur(to_grayscale(after), (5, 5), 1.0).astype(float)
    edge_a = cv2.magnitude(cv2.Sobel(gray_a, cv2.CV_64F, 1, 0), cv2.Sobel(gray_a, cv2.CV_64F, 0, 1))
    edge_b = cv2.magnitude(cv2.Sobel(gray_b, cv2.CV_64F, 1, 0), cv2.Sobel(gray_b, cv2.CV_64F, 0, 1))
    strong = edge_a > max(40.0, float(np.percentile(edge_a, 85)))
    retention = float(edge_b[strong].mean() / edge_a[strong].mean()) if strong.any() else 1.0
    return {
        "ssim": float(structural_similarity(before, after, channel_axis=-1, data_range=255)),
        "mean_absolute_change": float(np.abs(a - b).mean()),
        "chroma_change": float(np.abs(lab_a[..., 1:] - lab_b[..., 1:]).mean()),
        "edge_retention": retention,
    }


def apply_adaptive_filter_pipeline(
    image: np.ndarray,
    filters_config: dict[str, Any] | None = None,
    *,
    quality: ImageQualityMetrics | None = None,
    overrides: dict[str, Any] | None = None,
) -> AdaptiveFilterPipelineResult:
    source = ensure_uint8(image)
    config = dict(filters_config or {})
    automatic = dict(config.get("auto", {})) | dict(overrides or {})
    before = correction_diagnostics(source)
    proposals: list[tuple[str, str]] = []
    if before["impulse_ratio"] >= float(automatic.get("min_impulse_ratio", 0.0005)):
        proposals.append(("median", "ruído impulsivo isolado"))
    elif before["noise_sigma"] >= float(automatic.get("min_noise_sigma", 4.0)):
        proposals.extend([("bilateral", "ruído estimado"), ("gaussian", "ruído estimado")])
    if 8 < before["robust_range"] < 70 and before["noise_sigma"] < 6:
        proposals.append(("clahe", "faixa tonal reduzida"))

    allowed = automatic.get("candidate_sequences")
    if allowed:
        allowed_names = {step for sequence in allowed for step in
                         (sequence.split(",") if isinstance(sequence, str) else sequence)}
        proposals = [pair for pair in proposals if pair[0] in allowed_names]

    defaults = {
        "median": {"kernel_size": 3},
        "gaussian": {"kernel_size": 3, "sigma": 0.55},
        "bilateral": {"diameter": 5, "sigma_color": max(12, min(30, before["noise_sigma"] * 2)),
                      "sigma_space": 3},
        "clahe": {"clip_limit": 1.5, "tile_grid_size": [8, 8], "strength": 0.20},
    }
    selected = apply_filter(source, "none")
    selected_score = 0.0
    rows = [{"sequence": "none", "score": 0.0, "accepted": True, "reason": "controle sem alteração"}]
    skipped = []
    for method, diagnosis in proposals:
        parameters = defaults[method] | dict(automatic.get("method_parameters", {}).get(method, {}))
        try:
            candidate = apply_filter(source, method, parameters)
        except (FilterUnavailableError, ValueError) as exc:
            skipped.append({"sequence": method, "reason": str(exc)})
            continue
        if method == "median":
            impulse_mask = _impulse_mask(source)
            candidate = replace(candidate,
                image=np.where(impulse_mask[..., None], candidate.image, source),
                parameters=candidate.parameters | {"application": "isolated_impulse_pixels"})
        after = correction_diagnostics(candidate.image)
        preservation = _preservation(source, candidate.image)
        spatial_guard = preservation["edge_retention"] >= 0.85 and preservation["ssim"] >= 0.82
        if method == "median":
            gain = 1.0 - after["impulse_ratio"] / max(before["impulse_ratio"], 1e-6)
            sufficient = gain >= 0.5
            # Removing corruption may lower SSIM against the corrupt image. Require
            # exact preservation of every pixel outside the diagnosed impulses.
            untouched = np.array_equal(source[~impulse_mask], candidate.image[~impulse_mask])
            preservation["unaffected_pixels_preserved"] = bool(untouched)
            spatial_guard = untouched
        elif method == "clahe":
            gain = (after["robust_range"] - before["robust_range"]) / max(before["robust_range"], 1)
            sufficient = gain >= 0.04
        else:
            gain = 1.0 - after["noise_sigma"] / max(before["noise_sigma"], 1e-6)
            sufficient = gain >= 0.15
        guards = (
            spatial_guard
            and preservation["chroma_change"] <= 3.0
            and preservation["mean_absolute_change"] <= 10.0
            and after["clipped_ratio"] <= before["clipped_ratio"] + 0.005
        )
        accepted = bool(sufficient and guards)
        score = float(gain - preservation["mean_absolute_change"] / 100) if accepted else -1.0
        rows.append({"sequence": method, "score": round(score, 4), "accepted": accepted,
                     "reason": diagnosis if accepted else "ganho insuficiente ou perda de informação",
                     "before": before, "after": after, "preservation": preservation})
        if score > selected_score:
            selected, selected_score = candidate, score

    reason = ("Imagem preservada: nenhuma correção demonstrou ganho suficiente com os limites de preservação."
              if selected.name == "none" else
              f"{selected.name} aplicado após diagnóstico; limites de alteração de cor, contorno e intensidade atendidos.")
    decision = {"requested": "auto", "mode": "conservative_v2", "selected": selected.name,
                "selected_sequence": [selected.name], "reason": reason, "diagnostics": before,
                "candidates": rows, "skipped": skipped,
                "quality_issues": [diagnosis for _, diagnosis in proposals]}
    result = FilterResult(
        name=f"auto -> {selected.name}", image=selected.image,
        parameters={"sequence": [selected.name], "steps": [{"name": selected.name,
                    "parameters": selected.parameters, "dependency": selected.dependency}],
                    "score": round(selected_score, 4)},
        explanation=reason, dependency=selected.dependency,
    )
    return AdaptiveFilterPipelineResult(result, decision)
