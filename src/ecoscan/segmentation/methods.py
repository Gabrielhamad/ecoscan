from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ecoscan.image_processing.image_io import ensure_uint8


try:
    import cv2  # type: ignore
except ImportError:  # pragma: no cover - depends on optional environment.
    cv2 = None


class SegmentationUnavailableError(RuntimeError):
    """Raised when a segmentation method depends on an unavailable package."""


@dataclass(frozen=True)
class SegmentationResult:
    name: str
    mask: np.ndarray
    image: np.ndarray
    parameters: dict[str, Any]
    foreground_ratio: float
    explanation: str
    dependency: str


def _rgb_to_gray(image: np.ndarray) -> np.ndarray:
    rgb = ensure_uint8(image).astype(np.float32)
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.uint8)


def _saturation_and_value(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rgb = ensure_uint8(image).astype(np.float32) / 255.0
    max_channel = np.max(rgb, axis=2)
    min_channel = np.min(rgb, axis=2)
    saturation = np.zeros_like(max_channel)
    nonzero = max_channel > 0
    saturation[nonzero] = (max_channel[nonzero] - min_channel[nonzero]) / max_channel[nonzero]
    return saturation * 255.0, max_channel * 255.0


def apply_mask(image: np.ndarray, mask: np.ndarray, background: int = 255) -> np.ndarray:
    rgb = ensure_uint8(image)
    binary = mask > 0
    output = np.full_like(rgb, int(background), dtype=np.uint8)
    output[binary] = rgb[binary]
    return output


def _otsu_threshold(gray: np.ndarray) -> int:
    histogram = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    total = gray.size
    sum_total = np.dot(np.arange(256), histogram)

    sum_background = 0.0
    weight_background = 0.0
    best_variance = -1.0
    threshold = 0

    for level in range(256):
        weight_background += histogram[level]
        if weight_background == 0:
            continue
        weight_foreground = total - weight_background
        if weight_foreground == 0:
            break

        sum_background += level * histogram[level]
        mean_background = sum_background / weight_background
        mean_foreground = (sum_total - sum_background) / weight_foreground
        variance = weight_background * weight_foreground * (mean_background - mean_foreground) ** 2
        if variance > best_variance:
            best_variance = variance
            threshold = level
    return threshold


def segment_none(image: np.ndarray, **_: Any) -> SegmentationResult:
    mask = np.full(ensure_uint8(image).shape[:2], 255, dtype=np.uint8)
    return SegmentationResult(
        name="none",
        mask=mask,
        image=ensure_uint8(image).copy(),
        parameters={},
        foreground_ratio=1.0,
        explanation="Sem segmentação. Mantém todo o conteúdo como controle experimental.",
        dependency="numpy",
    )


def segment_otsu(image: np.ndarray, *, invert: bool | None = None, **_: Any) -> SegmentationResult:
    rgb = ensure_uint8(image)
    gray = _rgb_to_gray(rgb)
    threshold = _otsu_threshold(gray)
    light_mask = (gray > threshold).astype(np.uint8) * 255
    dark_mask = 255 - light_mask

    if invert is None:
        light_ratio = float(np.mean(light_mask > 0))
        dark_ratio = float(np.mean(dark_mask > 0))
        target_ratio = 0.45
        selected = dark_mask if abs(dark_ratio - target_ratio) < abs(light_ratio - target_ratio) else light_mask
        selected_inverted = selected is dark_mask
    else:
        selected = dark_mask if invert else light_mask
        selected_inverted = bool(invert)

    foreground_ratio = float(np.mean(selected > 0))
    return SegmentationResult(
        name="otsu",
        mask=selected,
        image=apply_mask(rgb, selected),
        parameters={"threshold": int(threshold), "invert": selected_inverted},
        foreground_ratio=foreground_ratio,
        explanation=(
            "Segmentação por Otsu em tons de cinza. Estima automaticamente um limiar global "
            "para separar regiões claras e escuras; funciona melhor com objeto e fundo contrastantes."
        ),
        dependency="numpy",
    )


def segment_hsv_color(
    image: np.ndarray,
    *,
    saturation_min: int = 45,
    value_min: int = 35,
    **_: Any,
) -> SegmentationResult:
    rgb = ensure_uint8(image)
    if cv2 is not None:
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        saturation = hsv[..., 1]
        value = hsv[..., 2]
        dependency = "opencv"
    else:
        saturation, value = _saturation_and_value(rgb)
        dependency = "numpy"
    mask = np.where((saturation >= int(saturation_min)) & (value >= int(value_min)), 255, 0)
    mask = mask.astype(np.uint8)
    return SegmentationResult(
        name="hsv_color",
        mask=mask,
        image=apply_mask(rgb, mask),
        parameters={"saturation_min": int(saturation_min), "value_min": int(value_min)},
        foreground_ratio=float(np.mean(mask > 0)),
        explanation=(
            "Segmenta pixels com saturação e brilho mínimos em HSV. Pode destacar resíduos coloridos, "
            "mas falha em objetos brancos, pretos, transparentes ou fundos coloridos."
        ),
        dependency=dependency,
    )


def segment_grabcut(
    image: np.ndarray,
    *,
    iterations: int = 5,
    margin_percent: float = 0.08,
    **_: Any,
) -> SegmentationResult:
    if cv2 is None:
        raise SegmentationUnavailableError("GrabCut requires opencv-python.")

    rgb = ensure_uint8(image)
    height, width = rgb.shape[:2]
    margin_x = max(1, int(width * float(margin_percent)))
    margin_y = max(1, int(height * float(margin_percent)))
    rectangle = (margin_x, margin_y, width - margin_x * 2, height - margin_y * 2)

    mask = np.zeros((height, width), np.uint8)
    bg_model = np.zeros((1, 65), np.float64)
    fg_model = np.zeros((1, 65), np.float64)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    cv2.grabCut(bgr, mask, rectangle, bg_model, fg_model, int(iterations), cv2.GC_INIT_WITH_RECT)
    binary = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

    return SegmentationResult(
        name="grabcut",
        mask=binary,
        image=apply_mask(rgb, binary),
        parameters={"iterations": int(iterations), "margin_percent": float(margin_percent)},
        foreground_ratio=float(np.mean(binary > 0)),
        explanation=(
            "GrabCut estima primeiro plano e fundo a partir de um retângulo central. "
            "É útil quando há um resíduo dominante centralizado, mas sensível a enquadramento."
        ),
        dependency="opencv",
    )


SEGMENTATION_METHODS = {
    "none": segment_none,
    "otsu": segment_otsu,
    "threshold": segment_otsu,
    "hsv_color": segment_hsv_color,
    "grabcut": segment_grabcut,
}


def segment_image(image: np.ndarray, name: str, parameters: dict[str, Any] | None = None) -> SegmentationResult:
    normalized_name = name.lower().strip()
    if normalized_name not in SEGMENTATION_METHODS:
        available = ", ".join(sorted(SEGMENTATION_METHODS))
        raise ValueError(f"Unknown segmentation method '{name}'. Available methods: {available}.")
    return SEGMENTATION_METHODS[normalized_name](image, **(parameters or {}))
