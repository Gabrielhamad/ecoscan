from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from ecoscan.image_processing.validation import ImageInfo, validate_image_file


@dataclass(frozen=True)
class LoadedImage:
    info: ImageInfo
    array: np.ndarray


def load_rgb_image(
    path: str | Path,
    *,
    allowed_extensions: set[str] | frozenset[str],
    min_size: tuple[int, int],
) -> LoadedImage:
    info = validate_image_file(
        path,
        allowed_extensions=allowed_extensions,
        min_size=min_size,
    )
    with Image.open(info.path) as image:
        image = ImageOps.exif_transpose(image)
        rgb = image.convert("RGB")
        array = np.asarray(rgb, dtype=np.uint8)
    return LoadedImage(info=info, array=array)


def array_to_pil(image: np.ndarray) -> Image.Image:
    if image.ndim == 2:
        return Image.fromarray(image.astype(np.uint8), mode="L")
    if image.ndim == 3 and image.shape[2] == 3:
        return Image.fromarray(image.astype(np.uint8), mode="RGB")
    raise ValueError(f"Unsupported image array shape: {image.shape}")


def save_image(image: np.ndarray, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    array_to_pil(image).save(output_path)
    return output_path


def ensure_uint8(image: np.ndarray) -> np.ndarray:
    if image.dtype == np.uint8:
        return image
    return np.clip(image, 0, 255).astype(np.uint8)

