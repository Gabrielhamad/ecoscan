"""Binary morphology with explicit footprint, order and border convention."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

OPERATIONS = {
    "none": "Sem morfologia (controle)",
    "erosion": "Erosão",
    "dilation": "Dilatação",
    "opening": "Abertura",
    "closing": "Fechamento",
    "open_close": "Abertura seguida de fechamento",
}
EXPLANATIONS = {
    "none": "Mantém a máscara segmentada como controle experimental.",
    "erosion": "Contrai o primeiro plano; pode separar regiões e eliminar detalhes finos.",
    "dilation": "Expande o primeiro plano; pode conectar fragmentos e unir objetos próximos.",
    "opening": "Erosão seguida de dilatação; remove regiões menores que o elemento estruturante.",
    "closing": "Dilatação seguida de erosão; preenche pequenas lacunas e pode unir regiões.",
    "open_close": "Abertura seguida de fechamento; remove ruído claro e pequenas lacunas escuras.",
}


@dataclass(frozen=True)
class MorphologyResult:
    mask: np.ndarray
    gradient: np.ndarray
    kernel: np.ndarray
    stages: tuple[tuple[str, np.ndarray], ...]
    metadata: dict


def structuring_element(size: int = 3, shape: str = "square") -> np.ndarray:
    if type(size) is not int or size not in range(1, 16, 2):
        raise ValueError("O elemento estruturante deve ter tamanho ímpar entre 1 e 15.")
    if shape not in ("square", "cross", "disk"):
        raise ValueError("Formato do elemento estruturante inválido.")
    radius = size // 2
    y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1]
    if shape == "cross":
        return ((x == 0) | (y == 0)).astype(np.uint8)
    if shape == "disk":
        return (x * x + y * y <= radius * radius).astype(np.uint8)
    return np.ones((size, size), dtype=np.uint8)


def _primitive(mask: np.ndarray, kernel: np.ndarray, *, dilate: bool, iterations: int):
    result = mask.copy()
    radius = kernel.shape[0] // 2
    height, width = mask.shape
    for _ in range(iterations):
        # Outside the finite image is background for BOTH erosion and dilation.
        padded = np.pad(result, radius, mode="constant", constant_values=False)
        reduced = np.zeros_like(result) if dilate else np.ones_like(result)
        for y, x in np.argwhere(kernel):
            neighbour = padded[y:y + height, x:x + width]
            if dilate:
                reduced |= neighbour
            else:
                reduced &= neighbour
        result = reduced
    return result


def apply_morphology(mask: np.ndarray, operation: str = "none", *,
                     kernel_size: int = 3, kernel_shape: str = "square",
                     iterations: int = 1) -> MorphologyResult:
    if operation not in OPERATIONS:
        raise ValueError("Operação morfológica inválida.")
    if type(iterations) is not int or not 1 <= iterations <= 5:
        raise ValueError("Use de 1 a 5 iterações por operação primitiva.")
    values = np.asarray(mask)
    if values.ndim != 2 or values.size == 0:
        raise ValueError("A morfologia exige uma máscara bidimensional não vazia.")
    if not np.isin(values, [0, 1, 255]).all():
        raise ValueError("A máscara deve ser binária (0/1 ou 0/255).")
    kernel = structuring_element(kernel_size, kernel_shape)
    original = values > 0
    sequence = {
        "none": (), "erosion": ("erosion",), "dilation": ("dilation",),
        "opening": ("erosion", "dilation"), "closing": ("dilation", "erosion"),
        "open_close": ("erosion", "dilation", "dilation", "erosion"),
    }[operation]
    current = original.copy()
    stages = []
    for primitive in sequence:
        current = _primitive(current, kernel, dilate=primitive == "dilation",
                             iterations=iterations)
        stages.append((primitive, current.astype(np.uint8) * 255))
    # The gradient is diagnostic, never used as the foreground mask for recognition.
    dilated = _primitive(current, kernel, dilate=True, iterations=iterations)
    eroded = _primitive(current, kernel, dilate=False, iterations=iterations)
    gradient = (dilated & ~eroded).astype(np.uint8) * 255
    before, after = int(original.sum()), int(current.sum())
    return MorphologyResult(
        mask=current.astype(np.uint8) * 255, gradient=gradient, kernel=kernel,
        stages=tuple(stages),
        metadata={
            "operation": operation, "kernel_size": kernel_size, "kernel_shape": kernel_shape,
            "kernel": kernel.tolist(), "anchor": [kernel_size // 2, kernel_size // 2],
            "iterations": iterations, "sequence": list(sequence),
            "iteration_semantics": "N repetições de cada primitiva, na ordem registrada.",
            "border": "constant background (0)", "foreground": "white (255)",
            "foreground_pixels_before": before, "foreground_pixels_after": after,
            "foreground_ratio_before": before / original.size,
            "foreground_ratio_after": after / original.size,
            "changed_pixels": int(np.count_nonzero(original != current)),
            "explanation": EXPLANATIONS[operation],
            "gradient": "Dilatação menos erosão da máscara final; somente visualização.",
            "dependency": "numpy",
        },
    )
