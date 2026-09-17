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
    visual_svm_model_exists: bool
    visual_model_exists: bool
    baseline_model_exists: bool
    final_model_path: str
    visual_svm_model_path: str
    visual_model_path: str
    baseline_model_path: str


def _is_installed(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def dependency_status() -> list[DependencyStatus]:
    return [
        DependencyStatus("Pillow", _is_installed("PIL"), "leitura, validação e fallback de filtros"),
        DependencyStatus("NumPy", _is_installed("numpy"), "arrays, features e cálculos de processamento"),
        DependencyStatus("OpenCV", _is_installed("cv2"), "bilateral, CLAHE real, Canny real, HSV, GrabCut e webcam direta por script"),
        DependencyStatus("scikit-image", _is_installed("skimage"), "experimentos avançados de segmentação"),
        DependencyStatus("TensorFlow", _is_installed("tensorflow"), "transfer learning e modelo final .keras"),
        DependencyStatus("Streamlit", _is_installed("streamlit"), "interface local de apresentação"),
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
    final_model_path = config.project_root / str(config.model.get("output_path", "models/ecoscan_transfer.keras"))
    visual_svm_model_path = config.directories["models"] / "vision_svm_classifier.joblib"
    visual_model_path = config.directories["models"] / "vision_classifier.npz"
    baseline_model_path = config.directories["models"] / "baseline_classifier.json"
    if final_model_path.exists():
        selected_kind = "transfer_learning"
        selected_path = str(final_model_path)
    elif visual_model_path.exists():
        selected_kind = "visual_knn"
        selected_path = str(visual_model_path)
    elif visual_svm_model_path.exists():
        selected_kind = "visual_svm"
        selected_path = str(visual_svm_model_path)
    elif baseline_model_path.exists():
        selected_kind = "baseline"
        selected_path = str(baseline_model_path)
    else:
        selected_kind = "none"
        selected_path = ""
    return ModelStatus(
        selected_kind=selected_kind,
        selected_path=selected_path,
        final_model_exists=final_model_path.exists(),
        visual_svm_model_exists=visual_svm_model_path.exists(),
        visual_model_exists=visual_model_path.exists(),
        baseline_model_exists=baseline_model_path.exists(),
        final_model_path=str(final_model_path),
        visual_svm_model_path=str(visual_svm_model_path),
        visual_model_path=str(visual_model_path),
        baseline_model_path=str(baseline_model_path),
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
