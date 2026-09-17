from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "settings.json"


class ConfigError(ValueError):
    """Raised when EcoScan configuration is invalid."""


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    config_path: Path
    project_name: str
    image_size: tuple[int, int]
    confidence_threshold: float
    random_seed: int
    allowed_extensions: frozenset[str]
    min_image_size: tuple[int, int]
    min_images_per_class_warning: int
    imbalance_ratio_warning: float
    classes: tuple[str, ...]
    directories: dict[str, Path]
    dataset_split: dict[str, float]
    baseline: dict[str, Any]
    model: dict[str, Any]
    history: dict[str, Any]
    filters: dict[str, Any]
    segmentation: dict[str, Any]


def _as_size(value: Any, key: str) -> tuple[int, int]:
    if not isinstance(value, list | tuple) or len(value) != 2:
        raise ConfigError(f"{key} must contain [width, height].")
    width, height = value
    if not isinstance(width, int) or not isinstance(height, int):
        raise ConfigError(f"{key} values must be integers.")
    if width <= 0 or height <= 0:
        raise ConfigError(f"{key} values must be positive.")
    return width, height


def _resolve_project_root(config_path: Path) -> Path:
    if config_path.name == "settings.json" and config_path.parent.name == "config":
        return config_path.parent.parent
    return PROJECT_ROOT


def load_config(config_path: str | Path | None = None) -> AppConfig:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    path = path.resolve()

    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    classes = tuple(raw.get("classes", []))
    if not classes:
        raise ConfigError("At least one class must be configured.")
    if len(classes) != len(set(classes)):
        raise ConfigError("Configured classes must be unique.")

    confidence_threshold = float(raw.get("confidence_threshold", 0.0))
    if not 0.0 <= confidence_threshold <= 1.0:
        raise ConfigError("confidence_threshold must be between 0 and 1.")

    allowed_extensions = frozenset(
        extension.lower() if str(extension).startswith(".") else f".{str(extension).lower()}"
        for extension in raw.get("allowed_extensions", [])
    )
    if not allowed_extensions:
        raise ConfigError("At least one image extension must be allowed.")

    project_root = _resolve_project_root(path)
    raw_directories = raw.get("directories", {})
    directories = {
        name: (project_root / directory).resolve()
        for name, directory in raw_directories.items()
    }

    return AppConfig(
        project_root=project_root,
        config_path=path,
        project_name=str(raw.get("project_name", "EcoScan")),
        image_size=_as_size(raw.get("image_size", [224, 224]), "image_size"),
        confidence_threshold=confidence_threshold,
        random_seed=int(raw.get("random_seed", 42)),
        allowed_extensions=allowed_extensions,
        min_image_size=_as_size(raw.get("min_image_size", [64, 64]), "min_image_size"),
        min_images_per_class_warning=int(raw.get("min_images_per_class_warning", 20)),
        imbalance_ratio_warning=float(raw.get("imbalance_ratio_warning", 2.0)),
        classes=classes,
        directories=directories,
        dataset_split=dict(raw.get("dataset_split", {"train": 0.7, "validation": 0.15, "test": 0.15})),
        baseline=dict(raw.get("baseline", {})),
        model=dict(raw.get("model", {})),
        history=dict(raw.get("history", {})),
        filters=dict(raw.get("filters", {})),
        segmentation=dict(raw.get("segmentation", {})),
    )
