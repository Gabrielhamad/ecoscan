from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

from ecoscan.image_processing.image_io import array_to_pil, ensure_uint8


@dataclass(frozen=True)
class PreprocessResult:
    resized: np.ndarray
    normalized: np.ndarray
    model_input: np.ndarray
    metadata: dict[str, object]


def resize_image(image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    width, height = size
    pil_image = array_to_pil(ensure_uint8(image))
    resized = pil_image.resize((width, height), resample=Image.Resampling.BICUBIC)
    return np.asarray(resized, dtype=np.uint8)


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """RGB luminance approximation; keep RGB separately for color recognition."""
    rgb = ensure_uint8(image).astype(np.float32)
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.uint8)


def normalize_image(image: np.ndarray) -> np.ndarray:
    return ensure_uint8(image).astype(np.float32) / 255.0


def prepare_model_input(image: np.ndarray, image_size: tuple[int, int]) -> PreprocessResult:
    resized = resize_image(image, image_size)
    normalized = normalize_image(resized)
    model_input = np.expand_dims(normalized, axis=0)
    return PreprocessResult(
        resized=resized,
        normalized=normalized,
        model_input=model_input,
        metadata={
            "target_size": list(image_size),
            "resize": "bicubic; stretch to target size (legacy model contract)",
            "source_shape": list(image.shape),
            "color_space": "RGB after EXIF orientation correction on load",
            "normalized_dtype": str(normalized.dtype),
            "normalized_range": [float(normalized.min()), float(normalized.max())],
            "normalization": "uint8 RGB scaled to [0, 1]",
            "model_input_shape": list(model_input.shape),
        },
    )


def model_input_preview(normalized_image: np.ndarray) -> np.ndarray:
    return np.clip(normalized_image * 255.0, 0, 255).astype(np.uint8)

