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


def prepare_working_image(image: np.ndarray, max_dimension: int = 640) -> PreprocessResult:
    """Keep geometry and sufficient detail; never upscale the inspection image."""
    height, width = image.shape[:2]
    limit = max(48, int(max_dimension))
    scale = min(1.0, limit / max(height, width))
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    if size == (width, height):
        resized = ensure_uint8(image).copy()
    else:
        import cv2
        resized = cv2.resize(ensure_uint8(image), size, interpolation=cv2.INTER_AREA)
    normalized = normalize_image(resized)
    return PreprocessResult(resized, normalized, normalized[None, ...], {
        "resize": "aspect ratio preserved; area resampling; no upscaling",
        "source_shape": list(image.shape), "target_size": list(size),
        "scale": scale, "color_space": "RGB after EXIF orientation correction",
    })


def letterbox_image(image: np.ndarray, size: tuple[int, int], padding: int = 127) -> tuple[np.ndarray, dict]:
    """Fit the entire frame into a fixed tensor, recording the content rectangle."""
    import cv2
    height, width = image.shape[:2]
    target_width, target_height = size
    scale = min(target_width / width, target_height / height)
    new_width, new_height = max(1, round(width * scale)), max(1, round(height * scale))
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR
    resized = cv2.resize(ensure_uint8(image), (new_width, new_height), interpolation=interpolation)
    left, top = (target_width - new_width) // 2, (target_height - new_height) // 2
    output = np.full((target_height, target_width, 3), int(padding), dtype=np.uint8)
    output[top:top + new_height, left:left + new_width] = resized
    return output, {"resize": "letterbox; no crop or stretching", "scale": scale,
                    "content_box_xywh": [left, top, new_width, new_height],
                    "padding_rgb": [padding] * 3, "target_size": list(size)}


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
