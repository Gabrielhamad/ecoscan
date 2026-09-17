from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class GuidanceError(ValueError):
    """Raised when disposal guidance cannot be loaded or resolved."""


@dataclass(frozen=True)
class DisposalGuidance:
    class_id: str
    display_name: str
    environmental_category: str
    common_trash: bool
    guidance: str
    educational_note: str
    academic_example: bool


def load_guidance(path: str | Path) -> dict[str, DisposalGuidance]:
    guidance_path = Path(path).resolve()
    if not guidance_path.exists():
        raise GuidanceError(f"Guidance file not found: {guidance_path}")

    with guidance_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    guidance: dict[str, DisposalGuidance] = {}
    for class_id, value in raw.items():
        guidance[class_id] = DisposalGuidance(
            class_id=class_id,
            display_name=str(value["display_name"]),
            environmental_category=str(value["environmental_category"]),
            common_trash=bool(value["common_trash"]),
            guidance=str(value["guidance"]),
            educational_note=str(value["educational_note"]),
            academic_example=bool(value.get("academic_example", True)),
        )
    return guidance


def get_guidance(class_id: str, guidance_by_class: dict[str, DisposalGuidance]) -> DisposalGuidance:
    try:
        return guidance_by_class[class_id]
    except KeyError as exc:
        raise GuidanceError(f"Unknown class without disposal guidance: {class_id}") from exc

