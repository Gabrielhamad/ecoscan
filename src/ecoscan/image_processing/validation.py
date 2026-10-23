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
    max_pixels: int = 40_000_000,
    max_file_bytes: int = 15 * 1024 * 1024,
) -> ImageInfo:
    if max_pixels <= 0 or max_file_bytes <= 0:
        raise ValueError('Image size limits must be positive.')
    image_path = Path(path)
    suffix = image_path.suffix.lower()
    if suffix not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise ImageValidationError(f"Unsupported image format '{suffix}'. Expected: {allowed}.")
    if not image_path.exists():
        raise ImageValidationError(f"Image file not found: {image_path}")
    if image_path.stat().st_size == 0:
        raise ImageValidationError("Image file is empty.")
    if image_path.stat().st_size > max_file_bytes:
        raise ImageValidationError(f'Arquivo muito grande. Limite: {max_file_bytes / (1024 * 1024):g} MB. Reduza seu tamanho.')

    try:
        with Image.open(image_path) as image:
            if image.width * image.height > max_pixels:
                raise ImageValidationError('Resolucao muito alta. Reduza as dimensoes da foto antes de enviar.')
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
    except Image.DecompressionBombError as exc:
        raise ImageValidationError('Resolucao muito alta. Reduza as dimensoes da foto antes de enviar.') from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageValidationError("Image file is corrupted or cannot be read.") from exc

