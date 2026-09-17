from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ecoscan.image_processing.preprocessing import resize_image


@dataclass(frozen=True)
class FeatureConfig:
    image_size: tuple[int, int] = (96, 96)
    histogram_bins: int = 8


def _rgb_to_gray(image: np.ndarray) -> np.ndarray:
    rgb = image.astype(np.float32)
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def _simple_edge_density(image: np.ndarray) -> float:
    gray = _rgb_to_gray(image)
    dx = np.abs(np.diff(gray, axis=1)).mean()
    dy = np.abs(np.diff(gray, axis=0)).mean()
    return float((dx + dy) / (2.0 * 255.0))


def extract_features(image: np.ndarray, config: FeatureConfig) -> np.ndarray:
    original_height, original_width = image.shape[:2]
    resized = resize_image(image, config.image_size).astype(np.float32)
    normalized = resized / 255.0

    color_mean = normalized.mean(axis=(0, 1))
    color_std = normalized.std(axis=(0, 1))
    histograms = []
    for channel in range(3):
        histogram, _ = np.histogram(
            normalized[..., channel],
            bins=config.histogram_bins,
            range=(0.0, 1.0),
            density=False,
        )
        histogram = histogram.astype(np.float32)
        histogram = histogram / max(1.0, histogram.sum())
        histograms.append(histogram)

    edge_density = np.array([_simple_edge_density(resized)], dtype=np.float32)
    aspect_hint = np.array([original_width / max(1, original_height)], dtype=np.float32)
    return np.concatenate([color_mean, color_std, *histograms, edge_density, aspect_hint]).astype(np.float32)


def feature_size(config: FeatureConfig) -> int:
    return 3 + 3 + 3 * config.histogram_bins + 2
