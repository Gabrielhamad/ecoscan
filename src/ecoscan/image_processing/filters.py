from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from PIL import ImageFilter

from ecoscan.image_processing.image_io import array_to_pil, ensure_uint8


try:
    import cv2  # type: ignore
except ImportError:  # pragma: no cover - exercised in environments without OpenCV.
    cv2 = None


class FilterUnavailableError(RuntimeError):
    """Raised when a requested filter needs an unavailable optional dependency."""


@dataclass(frozen=True)
class FilterResult:
    name: str
    image: np.ndarray
    parameters: dict[str, Any]
    explanation: str
    dependency: str


def _odd_kernel(value: int) -> int:
    value = int(value)
    if value < 1:
        raise ValueError("Kernel size must be positive.")
    return value if value % 2 == 1 else value + 1


def _rgb_to_gray(image: np.ndarray) -> np.ndarray:
    rgb = ensure_uint8(image).astype(np.float32)
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.float32)


def _gray_to_rgb(gray: np.ndarray) -> np.ndarray:
    clipped = np.clip(gray, 0, 255).astype(np.uint8)
    return np.repeat(clipped[..., None], 3, axis=2)


def apply_none(image: np.ndarray, **_: Any) -> FilterResult:
    return FilterResult(
        name="none",
        image=ensure_uint8(image).copy(),
        parameters={},
        explanation="Sem filtro. Serve como controle experimental para comparar impacto das técnicas.",
        dependency="numpy",
    )


def apply_gaussian(image: np.ndarray, *, kernel_size: int = 5, sigma: float = 1.0, **_: Any) -> FilterResult:
    kernel = _odd_kernel(kernel_size)
    if cv2 is not None:
        filtered = cv2.GaussianBlur(ensure_uint8(image), (kernel, kernel), sigmaX=float(sigma))
        dependency = "opencv"
    else:
        filtered = np.asarray(array_to_pil(image).filter(ImageFilter.GaussianBlur(radius=float(sigma))))
        dependency = "pillow fallback"
    return FilterResult(
        name="gaussian",
        image=ensure_uint8(filtered),
        parameters={"kernel_size": kernel, "sigma": float(sigma)},
        explanation="Suaviza ruído de alta frequência antes de segmentação por intensidade ou contornos.",
        dependency=dependency,
    )


def apply_median(image: np.ndarray, *, kernel_size: int = 5, **_: Any) -> FilterResult:
    kernel = _odd_kernel(kernel_size)
    if cv2 is not None:
        filtered = cv2.medianBlur(ensure_uint8(image), kernel)
        dependency = "opencv"
    else:
        filtered = np.asarray(array_to_pil(image).filter(ImageFilter.MedianFilter(size=kernel)))
        dependency = "pillow fallback"
    return FilterResult(
        name="median",
        image=ensure_uint8(filtered),
        parameters={"kernel_size": kernel},
        explanation="Reduz ruído impulsivo preservando bordas melhor que uma média simples.",
        dependency=dependency,
    )


def apply_bilateral(
    image: np.ndarray,
    *,
    diameter: int = 9,
    sigma_color: float = 75,
    sigma_space: float = 75,
    **_: Any,
) -> FilterResult:
    if cv2 is None:
        raise FilterUnavailableError("Bilateral filter requires opencv-python.")
    filtered = cv2.bilateralFilter(
        ensure_uint8(image),
        int(diameter),
        float(sigma_color),
        float(sigma_space),
    )
    return FilterResult(
        name="bilateral",
        image=ensure_uint8(filtered),
        parameters={
            "diameter": int(diameter),
            "sigma_color": float(sigma_color),
            "sigma_space": float(sigma_space),
        },
        explanation="Suaviza regiões semelhantes preservando descontinuidades fortes de borda.",
        dependency="opencv",
    )


def _global_histogram_equalization(gray: np.ndarray) -> np.ndarray:
    values = np.clip(gray, 0, 255).astype(np.uint8)
    hist = np.bincount(values.ravel(), minlength=256)
    cdf = hist.cumsum()
    nonzero = cdf[cdf > 0]
    if len(nonzero) == 0:
        return values
    cdf_min = nonzero[0]
    denominator = values.size - cdf_min
    if denominator <= 0:
        return values
    lookup = np.round((cdf - cdf_min) / denominator * 255.0).clip(0, 255).astype(np.uint8)
    return lookup[values]


def apply_clahe(
    image: np.ndarray,
    *,
    clip_limit: float = 2.0,
    tile_grid_size: tuple[int, int] | list[int] = (8, 8),
    **_: Any,
) -> FilterResult:
    rgb = ensure_uint8(image)
    if cv2 is not None:
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        lightness, channel_a, channel_b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=float(clip_limit), tileGridSize=tuple(tile_grid_size))
        enhanced = clahe.apply(lightness)
        merged = cv2.merge((enhanced, channel_a, channel_b))
        filtered = cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)
        dependency = "opencv"
        explanation = "Melhora contraste local no canal de luminosidade, útil quando iluminação é irregular."
    else:
        gray = _rgb_to_gray(rgb)
        equalized = _global_histogram_equalization(gray)
        filtered = _gray_to_rgb(equalized)
        dependency = "numpy fallback"
        explanation = (
            "Fallback sem OpenCV: equalização global de histograma em tons de cinza. "
            "Não substitui CLAHE, mas permite comparar melhoria de contraste."
        )
    return FilterResult(
        name="clahe",
        image=ensure_uint8(filtered),
        parameters={"clip_limit": float(clip_limit), "tile_grid_size": list(tile_grid_size)},
        explanation=explanation,
        dependency=dependency,
    )


def _convolve2d(gray: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    pad_h = kernel.shape[0] // 2
    pad_w = kernel.shape[1] // 2
    padded = np.pad(gray, ((pad_h, pad_h), (pad_w, pad_w)), mode="edge")
    output = np.zeros_like(gray, dtype=np.float32)
    for row in range(gray.shape[0]):
        for col in range(gray.shape[1]):
            region = padded[row:row + kernel.shape[0], col:col + kernel.shape[1]]
            output[row, col] = float(np.sum(region * kernel))
    return output


def _sobel_magnitude(image: np.ndarray) -> np.ndarray:
    gray = _rgb_to_gray(image)
    kernel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    kernel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)
    grad_x = _convolve2d(gray, kernel_x)
    grad_y = _convolve2d(gray, kernel_y)
    magnitude = np.sqrt(grad_x**2 + grad_y**2)
    if magnitude.max() > 0:
        magnitude = magnitude / magnitude.max() * 255.0
    return magnitude


def apply_sobel(image: np.ndarray, **_: Any) -> FilterResult:
    magnitude = _sobel_magnitude(image)
    return FilterResult(
        name="sobel",
        image=_gray_to_rgb(magnitude),
        parameters={},
        explanation="Realça bordas por gradiente; útil para analisar contornos do resíduo.",
        dependency="numpy",
    )


def apply_canny(
    image: np.ndarray,
    *,
    threshold1: int = 80,
    threshold2: int = 160,
    **_: Any,
) -> FilterResult:
    if cv2 is not None:
        edges = cv2.Canny(ensure_uint8(image), int(threshold1), int(threshold2))
        dependency = "opencv"
        explanation = "Detecta bordas com supressão de não máximos e histerese, útil para contornos."
    else:
        magnitude = _sobel_magnitude(image)
        edges = np.where(magnitude >= int(threshold2), 255, 0).astype(np.uint8)
        dependency = "numpy fallback"
        explanation = (
            "Fallback sem OpenCV: limiar alto sobre magnitude Sobel. "
            "Não substitui o Canny completo, mas permite uma comparação inicial de bordas."
        )
    return FilterResult(
        name="canny",
        image=_gray_to_rgb(edges),
        parameters={"threshold1": int(threshold1), "threshold2": int(threshold2)},
        explanation=explanation,
        dependency=dependency,
    )


FILTERS: dict[str, Callable[..., FilterResult]] = {
    "none": apply_none,
    "gaussian": apply_gaussian,
    "median": apply_median,
    "bilateral": apply_bilateral,
    "clahe": apply_clahe,
    "sobel": apply_sobel,
    "canny": apply_canny,
}


def apply_filter(image: np.ndarray, name: str, parameters: dict[str, Any] | None = None) -> FilterResult:
    normalized_name = name.lower().strip()
    if normalized_name not in FILTERS:
        available = ", ".join(sorted(FILTERS))
        raise ValueError(f"Unknown filter '{name}'. Available filters: {available}.")
    return FILTERS[normalized_name](image, **(parameters or {}))

