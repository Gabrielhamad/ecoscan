from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from ecoscan.image_processing.image_io import ensure_uint8


@dataclass(frozen=True)
class ImageQualityMetrics:
    brightness_mean: float
    brightness_std: float
    contrast: float
    sharpness: float
    saturation_mean: float
    edge_density: float
    exposure_status: str
    contrast_status: str
    focus_status: str
    recommendation: str

    def to_dict(self) -> dict[str, float | str]:
        return asdict(self)


def _rgb_to_gray(image: np.ndarray) -> np.ndarray:
    rgb = ensure_uint8(image).astype(np.float32)
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def _saturation_mean(image: np.ndarray) -> float:
    rgb = ensure_uint8(image).astype(np.float32) / 255.0
    max_channel = np.max(rgb, axis=2)
    min_channel = np.min(rgb, axis=2)
    saturation = np.zeros_like(max_channel)
    nonzero = max_channel > 0
    saturation[nonzero] = (max_channel[nonzero] - min_channel[nonzero]) / max_channel[nonzero]
    return float(np.mean(saturation))


def _laplacian(gray: np.ndarray) -> np.ndarray:
    padded = np.pad(gray, ((1, 1), (1, 1)), mode="edge")
    center = padded[1:-1, 1:-1] * -4.0
    return (
        center
        + padded[:-2, 1:-1]
        + padded[2:, 1:-1]
        + padded[1:-1, :-2]
        + padded[1:-1, 2:]
    )


def _sobel_magnitude(gray: np.ndarray) -> np.ndarray:
    padded = np.pad(gray, ((1, 1), (1, 1)), mode="edge")
    gx = (
        -padded[:-2, :-2]
        + padded[:-2, 2:]
        - 2.0 * padded[1:-1, :-2]
        + 2.0 * padded[1:-1, 2:]
        - padded[2:, :-2]
        + padded[2:, 2:]
    )
    gy = (
        -padded[:-2, :-2]
        - 2.0 * padded[:-2, 1:-1]
        - padded[:-2, 2:]
        + padded[2:, :-2]
        + 2.0 * padded[2:, 1:-1]
        + padded[2:, 2:]
    )
    return np.sqrt(gx**2 + gy**2)


def analyze_image_quality(image: np.ndarray) -> ImageQualityMetrics:
    gray = _rgb_to_gray(image)
    brightness_mean = float(np.mean(gray))
    brightness_std = float(np.std(gray))
    contrast = brightness_std / 255.0
    sharpness = float(np.var(_laplacian(gray)) / (255.0**2))
    gradient = _sobel_magnitude(gray)
    edge_density = float(np.mean(gradient > 35.0))
    saturation_mean = _saturation_mean(image)

    if brightness_mean < 70.0:
        exposure_status = "underexposed"
    elif brightness_mean > 205.0:
        exposure_status = "overexposed"
    else:
        exposure_status = "ok"

    contrast_status = "low" if contrast < 0.18 else "ok"
    focus_status = "low" if sharpness < 0.002 else "ok"

    if exposure_status != "ok" or contrast_status == "low":
        recommendation = "priorizar melhoria de contraste antes da segmentação"
    elif focus_status == "low":
        recommendation = "capturar nova imagem mais nítida; filtro não recupera detalhe perdido"
    elif edge_density > 0.35:
        recommendation = "usar suavização leve para reduzir excesso de bordas antes da segmentação"
    else:
        recommendation = "imagem adequada para pipeline padrão"

    return ImageQualityMetrics(
        brightness_mean=round(brightness_mean, 3),
        brightness_std=round(brightness_std, 3),
        contrast=round(contrast, 5),
        sharpness=round(sharpness, 5),
        saturation_mean=round(saturation_mean, 5),
        edge_density=round(edge_density, 5),
        exposure_status=exposure_status,
        contrast_status=contrast_status,
        focus_status=focus_status,
        recommendation=recommendation,
    )


def recommend_filter_name(metrics: ImageQualityMetrics) -> tuple[str, str]:
    if metrics.exposure_status != "ok" or metrics.contrast_status == "low":
        return "clahe", "baixo contraste ou exposição fora do intervalo ideal"
    if metrics.edge_density > 0.35:
        return "median", "densidade de bordas alta sugere ruído visual ou fundo complexo"
    return "gaussian", "imagem adequada para suavização leve antes da segmentação"
