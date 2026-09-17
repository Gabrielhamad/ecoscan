from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from skimage.color import rgb2gray
from skimage.feature import hog, local_binary_pattern

from ecoscan.image_processing.preprocessing import resize_image


@dataclass(frozen=True)
class VisualFeatureConfig:
    image_size: tuple[int, int] = (128, 128)
    rgb_histogram_bins: int = 16
    hsv_histogram_bins: int = 12
    hog_orientations: int = 9
    hog_pixels_per_cell: tuple[int, int] = (16, 16)
    hog_cells_per_block: tuple[int, int] = (2, 2)
    lbp_points: int = 16
    lbp_radius: int = 2

    def to_dict(self) -> dict[str, object]:
        return {
            "image_size": list(self.image_size),
            "rgb_histogram_bins": self.rgb_histogram_bins,
            "hsv_histogram_bins": self.hsv_histogram_bins,
            "hog_orientations": self.hog_orientations,
            "hog_pixels_per_cell": list(self.hog_pixels_per_cell),
            "hog_cells_per_block": list(self.hog_cells_per_block),
            "lbp_points": self.lbp_points,
            "lbp_radius": self.lbp_radius,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "VisualFeatureConfig":
        return cls(
            image_size=tuple(data.get("image_size", [128, 128])),  # type: ignore[arg-type]
            rgb_histogram_bins=int(data.get("rgb_histogram_bins", 16)),
            hsv_histogram_bins=int(data.get("hsv_histogram_bins", 12)),
            hog_orientations=int(data.get("hog_orientations", 9)),
            hog_pixels_per_cell=tuple(data.get("hog_pixels_per_cell", [16, 16])),  # type: ignore[arg-type]
            hog_cells_per_block=tuple(data.get("hog_cells_per_block", [2, 2])),  # type: ignore[arg-type]
            lbp_points=int(data.get("lbp_points", 16)),
            lbp_radius=int(data.get("lbp_radius", 2)),
        )


def _normalized_histogram(values: np.ndarray, *, bins: int, value_range: tuple[float, float]) -> np.ndarray:
    histogram, _ = np.histogram(values, bins=bins, range=value_range)
    histogram = histogram.astype(np.float32)
    return histogram / max(1.0, float(histogram.sum()))


def extract_visual_features(image: np.ndarray, config: VisualFeatureConfig) -> np.ndarray:
    resized = resize_image(image, config.image_size)
    rgb = resized.astype(np.float32) / 255.0

    features: list[np.ndarray] = []
    features.append(rgb.mean(axis=(0, 1)).astype(np.float32))
    features.append(rgb.std(axis=(0, 1)).astype(np.float32))

    for channel in range(3):
        features.append(
            _normalized_histogram(
                rgb[..., channel],
                bins=config.rgb_histogram_bins,
                value_range=(0.0, 1.0),
            )
        )

    hsv = cv2.cvtColor(resized, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[..., 0] /= 179.0
    hsv[..., 1:] /= 255.0
    for channel in range(3):
        features.append(
            _normalized_histogram(
                hsv[..., channel],
                bins=config.hsv_histogram_bins,
                value_range=(0.0, 1.0),
            )
        )

    gray = rgb2gray(rgb)
    hog_features = hog(
        gray,
        orientations=config.hog_orientations,
        pixels_per_cell=config.hog_pixels_per_cell,
        cells_per_block=config.hog_cells_per_block,
        block_norm="L2-Hys",
        feature_vector=True,
    ).astype(np.float32)
    features.append(hog_features)

    gray_uint8 = np.clip(gray * 255.0, 0, 255).astype(np.uint8)
    lbp = local_binary_pattern(
        gray_uint8,
        P=config.lbp_points,
        R=config.lbp_radius,
        method="uniform",
    )
    features.append(
        _normalized_histogram(
            lbp,
            bins=config.lbp_points + 2,
            value_range=(0.0, float(config.lbp_points + 2)),
        )
    )

    return np.concatenate(features).astype(np.float32)


def visual_feature_size(config: VisualFeatureConfig) -> int:
    sample = np.zeros((*reversed(config.image_size), 3), dtype=np.uint8)
    return int(extract_visual_features(sample, config).shape[0])
