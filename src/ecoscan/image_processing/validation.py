from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError


class ImageValidationError(ValueError):
    """Raised when an input image is not acceptable for EcoScan."""


@dataclass(frozen=True)
class ImageInfo:
    path: Path
    width: int
    height: int
    mode: str
    format: str | None


def validate_image_file(
    path: str | Path,
    *,
    allowed_extensions: set[str] | frozenset[str],
    min_size: tuple[int, int],
) -> ImageInfo:
    image_path = Path(path)
    suffix = image_path.suffix.lower()
    if suffix not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise ImageValidationError(f"Unsupported image format '{suffix}'. Expected: {allowed}.")
    if not image_path.exists():
        raise ImageValidationError(f"Image file not found: {image_path}")
    if image_path.stat().st_size == 0:
        raise ImageValidationError("Image file is empty.")

    try:
        with Image.open(image_path) as image:
            image.verify()
        with Image.open(image_path) as image:
            width, height = image.size
            if width < min_size[0] or height < min_size[1]:
                raise ImageValidationError(
                    f"Image is too small: {width}x{height}. Minimum: {min_size[0]}x{min_size[1]}."
                )
            return ImageInfo(
                path=image_path,
                width=width,
                height=height,
                mode=image.mode,
                format=image.format,
            )
    except ImageValidationError:
        raise
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageValidationError("Image file is corrupted or cannot be read.") from exc

