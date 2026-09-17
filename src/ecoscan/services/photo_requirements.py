from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PhotoRequirementError(ValueError):
    """Raised when photo collection requirements cannot be loaded."""


@dataclass(frozen=True)
class PhotoRequirement:
    class_id: str
    title: str
    minimum_images: int
    ideal_images: int
    examples: tuple[str, ...]
    contexts: tuple[str, ...]
    avoid: tuple[str, ...]


def load_photo_requirements(path: str | Path) -> dict[str, PhotoRequirement]:
    requirement_path = Path(path).resolve()
    if not requirement_path.exists():
        raise PhotoRequirementError(f"Photo requirement file not found: {requirement_path}")

    with requirement_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    requirements: dict[str, PhotoRequirement] = {}
    for class_id, value in raw.items():
        if not isinstance(value, dict):
            raise PhotoRequirementError(f"Invalid photo requirement for class: {class_id}")
        requirements[class_id] = _build_requirement(class_id, value)
    return requirements


def missing_requirements_for_classes(
    class_ids: tuple[str, ...] | list[str],
    requirements_by_class: dict[str, PhotoRequirement],
) -> list[str]:
    return [class_id for class_id in class_ids if class_id not in requirements_by_class]


def _build_requirement(class_id: str, value: dict[str, Any]) -> PhotoRequirement:
    required = ["title", "minimum_images", "ideal_images", "examples", "contexts", "avoid"]
    missing = [key for key in required if key not in value]
    if missing:
        raise PhotoRequirementError(
            f"Photo requirement for {class_id} is missing fields: {', '.join(missing)}"
        )

    examples = _as_text_tuple(value["examples"], class_id, "examples")
    contexts = _as_text_tuple(value["contexts"], class_id, "contexts")
    avoid = _as_text_tuple(value["avoid"], class_id, "avoid")
    minimum_images = int(value["minimum_images"])
    ideal_images = int(value["ideal_images"])
    if minimum_images <= 0 or ideal_images < minimum_images:
        raise PhotoRequirementError(
            f"Photo requirement for {class_id} has invalid minimum/ideal image counts."
        )

    return PhotoRequirement(
        class_id=class_id,
        title=str(value["title"]),
        minimum_images=minimum_images,
        ideal_images=ideal_images,
        examples=examples,
        contexts=contexts,
        avoid=avoid,
    )


def _as_text_tuple(value: Any, class_id: str, key: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise PhotoRequirementError(f"Photo requirement for {class_id} needs a non-empty {key} list.")
    return tuple(str(item) for item in value)
