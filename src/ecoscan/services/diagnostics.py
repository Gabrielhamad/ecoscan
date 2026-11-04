from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path

from ecoscan.config import AppConfig


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    installed: bool
    purpose: str


@dataclass(frozen=True)
class DatasetStatus:
    raw_counts: dict[str, int]
    curated_counts: dict[str, int]
    train_counts: dict[str, int]
    validation_counts: dict[str, int]
    test_counts: dict[str, int]


@dataclass(frozen=True)
class ModelStatus:
    selected_kind: str
    selected_path: str
    final_model_exists: bool
    final_model_path: str


def _is_installed(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def dependency_status() -> list[DependencyStatus]:
    return [
        DependencyStatus("Pillow", _is_installed("PIL"), "leitura e validação de imagens"),
        DependencyStatus("NumPy", _is_installed("numpy"), "arrays e cálculos de processamento"),
        DependencyStatus("OpenCV", _is_installed("cv2"), "bilateral, CLAHE real, Canny real, HSV, GrabCut e webcam direta por script"),
        DependencyStatus("scikit-image", _is_installed("skimage"), "métricas de imagem"),
        DependencyStatus("Streamlit", _is_installed("streamlit"), "interface local de apresentação"),
        DependencyStatus("ONNX Runtime", _is_installed("onnxruntime"), "inferência do reconhecedor atual"),
    ]


def _count_images(directory: Path, classes: tuple[str, ...], allowed_extensions: frozenset[str]) -> dict[str, int]:
    counts = {class_id: 0 for class_id in classes}
    for class_id in classes:
        class_dir = directory / class_id
        if not class_dir.exists():
            continue
        counts[class_id] = sum(
            1 for path in class_dir.iterdir()
            if path.is_file() and path.suffix.lower() in allowed_extensions
        )
    return counts


def dataset_status(config: AppConfig) -> DatasetStatus:
    return DatasetStatus(
        raw_counts=_count_images(config.directories["raw_data"], config.classes, config.allowed_extensions),
        curated_counts=_count_images(config.directories["curated_data"], config.classes, config.allowed_extensions),
        train_counts=_count_images(config.directories["train_data"], config.classes, config.allowed_extensions),
        validation_counts=_count_images(config.directories["validation_data"], config.classes, config.allowed_extensions),
        test_counts=_count_images(config.directories["test_data"], config.classes, config.allowed_extensions),
    )


def model_status(config: AppConfig) -> ModelStatus:
    from ecoscan.classification.runtime import ENGINE, configured_model_path

    final_model_path = configured_model_path(config)
    exists = final_model_path.is_file()
    return ModelStatus(
        selected_kind=ENGINE if exists else "none",
        selected_path=str(final_model_path) if exists else "",
        final_model_exists=exists,
        final_model_path=str(final_model_path),
    )


def write_diagnostics_report(config: AppConfig, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "dependencies": [item.__dict__ for item in dependency_status()],
        "dataset": dataset_status(config).__dict__,
        "model": model_status(config).__dict__,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
