from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ecoscan.image_processing.image_io import array_to_pil, ensure_uint8


@dataclass(frozen=True)
class VisualElement:
    label: int
    bbox_xyxy: tuple[int, int, int, int]
    centroid_xy: tuple[float, float]
    area_pixels: int
    area_ratio: float
    touches_border: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ElementAnalysis:
    image_width: int
    image_height: int
    element_count: int
    significant_count: int
    foreground_ratio: float
    largest_area_ratio: float
    likely_multi_object: bool
    warning: str
    elements: tuple[VisualElement, ...]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["elements"] = [element.to_dict() for element in self.elements]
        return data


def _neighbors(row: int, col: int, height: int, width: int):
    for next_row, next_col in (
        (row - 1, col),
        (row + 1, col),
        (row, col - 1),
        (row, col + 1),
    ):
        if 0 <= next_row < height and 0 <= next_col < width:
            yield next_row, next_col


def _component(
    binary: np.ndarray,
    visited: np.ndarray,
    start_row: int,
    start_col: int,
    label: int,
) -> VisualElement:
    height, width = binary.shape
    queue: deque[tuple[int, int]] = deque([(start_row, start_col)])
    visited[start_row, start_col] = True
    min_row = max_row = start_row
    min_col = max_col = start_col
    area = 0
    sum_row = 0
    sum_col = 0
    touches_border = False

    while queue:
        row, col = queue.popleft()
        area += 1
        sum_row += row
        sum_col += col
        min_row = min(min_row, row)
        max_row = max(max_row, row)
        min_col = min(min_col, col)
        max_col = max(max_col, col)
        touches_border = touches_border or row in {0, height - 1} or col in {0, width - 1}

        for next_row, next_col in _neighbors(row, col, height, width):
            if binary[next_row, next_col] and not visited[next_row, next_col]:
                visited[next_row, next_col] = True
                queue.append((next_row, next_col))

    return VisualElement(
        label=label,
        bbox_xyxy=(min_col, min_row, max_col + 1, max_row + 1),
        centroid_xy=(round(sum_col / area, 2), round(sum_row / area, 2)),
        area_pixels=area,
        area_ratio=round(area / float(height * width), 5),
        touches_border=touches_border,
    )


def analyze_visual_elements(
    mask: np.ndarray,
    *,
    min_area_ratio: float = 0.0025,
    max_elements: int = 12,
) -> ElementAnalysis:
    binary = np.asarray(mask) > 0
    height, width = binary.shape
    visited = np.zeros_like(binary, dtype=bool)
    min_area = max(1, int(binary.size * float(min_area_ratio)))
    elements: list[VisualElement] = []
    label = 1

    for row in range(height):
        for col in range(width):
            if not binary[row, col] or visited[row, col]:
                continue
            element = _component(binary, visited, row, col, label)
            label += 1
            if element.area_pixels >= min_area:
                elements.append(element)

    elements.sort(key=lambda item: item.area_pixels, reverse=True)
    selected = tuple(elements[:max_elements])
    foreground_ratio = float(np.mean(binary))
    largest_area_ratio = selected[0].area_ratio if selected else 0.0
    likely_multi_object = len([item for item in selected if item.area_ratio >= 0.01]) > 1

    if not selected:
        warning = "nenhum elemento visual significativo foi separado pela segmentação"
    elif foreground_ratio > 0.92:
        warning = "máscara cobre quase toda a imagem; segmentação não isolou o resíduo"
    elif likely_multi_object:
        warning = "há múltiplos componentes relevantes; o MVP classifica apenas um resíduo principal"
    elif selected[0].touches_border:
        warning = "elemento principal toca a borda; a imagem pode estar cortada"
    else:
        warning = "segmentação isolou um elemento principal de forma plausível"

    return ElementAnalysis(
        image_width=width,
        image_height=height,
        element_count=len(elements),
        significant_count=len(selected),
        foreground_ratio=round(foreground_ratio, 5),
        largest_area_ratio=round(largest_area_ratio, 5),
        likely_multi_object=likely_multi_object,
        warning=warning,
        elements=selected,
    )


def draw_element_overlay(image: np.ndarray, analysis: ElementAnalysis) -> np.ndarray:
    pil = array_to_pil(ensure_uint8(image)).convert("RGB")
    draw = ImageDraw.Draw(pil)
    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except OSError:
        font = ImageFont.load_default()

    palette = ["#1f7a5c", "#b26a00", "#365a96", "#8a3ffc", "#b83280", "#3c6e71"]
    for index, element in enumerate(analysis.elements):
        color = palette[index % len(palette)]
        x1, y1, x2, y2 = element.bbox_xyxy
        draw.rectangle((x1, y1, x2, y2), outline=color, width=3)
        label = f"{element.label}: {element.area_ratio * 100:.1f}%"
        draw.rectangle((x1, max(0, y1 - 18), min(x2, x1 + 92), y1), fill=color)
        draw.text((x1 + 4, max(0, y1 - 17)), label, fill="white", font=font)
    return np.asarray(pil, dtype=np.uint8)


def draw_detection_heatmap(image: np.ndarray, mask: np.ndarray, analysis: ElementAnalysis) -> np.ndarray:
    base = ensure_uint8(image)
    binary = np.asarray(mask) > 0
    if binary.ndim != 2:
        return base.copy()

    heat_source = Image.fromarray((binary.astype(np.uint8) * 255), mode="L").filter(ImageFilter.GaussianBlur(radius=7))
    heat = np.asarray(heat_source, dtype=np.float32) / 255.0
    if heat.max() > 0:
        heat = heat / heat.max()

    heat_rgb = np.zeros_like(base, dtype=np.float32)
    heat_rgb[..., 0] = 255.0
    heat_rgb[..., 1] = np.clip(heat * 225.0, 60.0, 225.0)
    heat_rgb[..., 2] = np.clip((1.0 - heat) * 70.0, 0.0, 70.0)

    alpha = np.clip(heat * 0.56, 0.0, 0.56)[..., None]
    blended = base.astype(np.float32) * (1.0 - alpha) + heat_rgb * alpha
    pil = array_to_pil(blended.clip(0, 255).astype(np.uint8)).convert("RGB")
    draw = ImageDraw.Draw(pil)
    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except OSError:
        font = ImageFont.load_default()

    for index, element in enumerate(analysis.elements):
        x1, y1, x2, y2 = element.bbox_xyxy
        color = "#fff176" if index == 0 else "#80d8ff"
        draw.rectangle((x1, y1, x2, y2), outline=color, width=3)
        label = "objeto principal" if index == 0 else f"elemento {element.label}"
        label_width = min(x2, x1 + 128)
        draw.rectangle((x1, max(0, y1 - 19), label_width, y1), fill="#17342a")
        draw.text((x1 + 4, max(0, y1 - 17)), label, fill="white", font=font)

    return np.asarray(pil, dtype=np.uint8)
