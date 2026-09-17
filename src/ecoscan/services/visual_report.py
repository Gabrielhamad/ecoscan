from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ecoscan.app.pipeline import ProcessingPipelineResult
from ecoscan.image_processing.filters import FilterResult
from ecoscan.image_processing.image_io import array_to_pil, ensure_uint8, save_image
from ecoscan.segmentation.methods import SegmentationResult


def _load_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _fit_image(image: np.ndarray, box_size: tuple[int, int]) -> Image.Image:
    pil = array_to_pil(ensure_uint8(image)).convert("RGB")
    pil.thumbnail(box_size)
    canvas = Image.new("RGB", box_size, "white")
    x = (box_size[0] - pil.width) // 2
    y = (box_size[1] - pil.height) // 2
    canvas.paste(pil, (x, y))
    return canvas


def _grid(items: list[tuple[str, np.ndarray]], output_path: Path, columns: int = 3) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cell_w = 260
    cell_h = 230
    label_h = 34
    rows = (len(items) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * cell_w, rows * (cell_h + label_h)), "white")
    draw = ImageDraw.Draw(canvas)
    font = _load_font(14)

    for index, (label, image) in enumerate(items):
        row = index // columns
        col = index % columns
        x = col * cell_w
        y = row * (cell_h + label_h)
        preview = _fit_image(image, (cell_w, cell_h))
        canvas.paste(preview, (x, y))
        draw.text((x + 8, y + cell_h + 8), label[:34], fill="black", font=font)

    canvas.save(output_path)
    return output_path


def _mask_to_rgb(mask: np.ndarray) -> np.ndarray:
    return np.repeat(mask[..., None], 3, axis=2).astype(np.uint8)


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return {
            "shape": list(value.shape),
            "dtype": str(value.dtype),
        }
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable.")


def save_pipeline_artifacts(result: ProcessingPipelineResult, output_dir: str | Path) -> list[Path]:
    report_dir = Path(output_dir).resolve()
    report_dir.mkdir(parents=True, exist_ok=True)

    artifacts = [
        save_image(result.loaded.array, report_dir / "01_original.jpg"),
        save_image(result.preprocessing.resized, report_dir / "02_resized.jpg"),
        save_image(result.filter_result.image, report_dir / "03_filtered.jpg"),
        save_image(_mask_to_rgb(result.segmentation_result.mask), report_dir / "04_segmentation_mask.jpg"),
        save_image(result.segmentation_result.image, report_dir / "05_segmented.jpg"),
        save_image(result.model_input_preview, report_dir / "06_model_input_preview.jpg"),
        save_image(result.element_overlay, report_dir / "07_elements_overlay.jpg"),
        save_image(result.detection_heatmap, report_dir / "08_detection_heatmap.jpg"),
    ]
    overview = _grid(
        [
            ("1 original", result.loaded.array),
            ("2 redimensionada", result.preprocessing.resized),
            (f"3 filtro: {result.filter_result.name}", result.filter_result.image),
            (f"4 segmentacao: {result.segmentation_result.name}", _mask_to_rgb(result.segmentation_result.mask)),
            ("5 imagem segmentada", result.segmentation_result.image),
            ("6 entrada do modelo", result.model_input_preview),
            ("7 elementos visuais", result.element_overlay),
            ("8 mapa de deteccao", result.detection_heatmap),
        ],
        report_dir / "pipeline_overview.jpg",
    )
    artifacts.append(overview)

    metadata_path = report_dir / "pipeline_report.json"
    metadata_path.write_text(json.dumps(result.metadata, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    artifacts.append(metadata_path)
    return artifacts


def save_filter_comparison(results: list[FilterResult], original: np.ndarray, output_dir: str | Path) -> list[Path]:
    report_dir = Path(output_dir).resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[Path] = []

    grid_items = [("original", original)] + [(result.name, result.image) for result in results]
    artifacts.append(_grid(grid_items, report_dir / "filter_comparison.jpg", columns=3))
    metadata = [
        {
            "name": result.name,
            "parameters": result.parameters,
            "dependency": result.dependency,
            "explanation": result.explanation,
        }
        for result in results
    ]
    metadata_path = report_dir / "filter_comparison.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    artifacts.append(metadata_path)
    return artifacts


def save_segmentation_comparison(results: list[SegmentationResult], original: np.ndarray, output_dir: str | Path) -> list[Path]:
    report_dir = Path(output_dir).resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[Path] = []

    grid_items: list[tuple[str, np.ndarray]] = [("original", original)]
    for result in results:
        grid_items.append((f"{result.name} mascara", _mask_to_rgb(result.mask)))
        grid_items.append((f"{result.name} resultado", result.image))
    artifacts.append(_grid(grid_items, report_dir / "segmentation_comparison.jpg", columns=3))

    metadata = [
        {
            "name": result.name,
            "parameters": result.parameters,
            "dependency": result.dependency,
            "foreground_ratio": result.foreground_ratio,
            "explanation": result.explanation,
        }
        for result in results
    ]
    metadata_path = report_dir / "segmentation_comparison.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    artifacts.append(metadata_path)
    return artifacts
