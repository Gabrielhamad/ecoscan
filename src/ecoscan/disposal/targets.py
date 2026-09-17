from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus


class DisposalTargetError(ValueError):
    """Raised when visual disposal target metadata cannot be loaded."""


@dataclass(frozen=True)
class DisposalTarget:
    class_id: str
    destination_title: str
    destination_type: str
    bin_color_name: str
    bin_color_hex: str
    asset_path: str
    search_query: str
    preparation_steps: tuple[str, ...]
    attention_note: str

    def asset_absolute_path(self, project_root: Path) -> Path:
        return (project_root / self.asset_path).resolve()


def load_disposal_targets(path: str | Path) -> dict[str, DisposalTarget]:
    target_path = Path(path).resolve()
    if not target_path.exists():
        raise DisposalTargetError(f"Disposal target file not found: {target_path}")

    with target_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    targets: dict[str, DisposalTarget] = {}
    for class_id, value in raw.items():
        if not isinstance(value, dict):
            raise DisposalTargetError(f"Invalid disposal target for class: {class_id}")
        targets[class_id] = _build_target(class_id, value)
    return targets


def get_disposal_target(
    class_id: str,
    targets_by_class: dict[str, DisposalTarget],
) -> DisposalTarget:
    try:
        return targets_by_class[class_id]
    except KeyError as exc:
        raise DisposalTargetError(f"Unknown class without disposal target: {class_id}") from exc


def build_map_search_url(search_query: str, location_text: str | None = None) -> str:
    parts = [search_query.strip()]
    if location_text and location_text.strip():
        parts.append(location_text.strip())
    query = " ".join(part for part in parts if part)
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)


def missing_targets_for_classes(
    class_ids: tuple[str, ...] | list[str],
    targets_by_class: dict[str, DisposalTarget],
) -> list[str]:
    return [class_id for class_id in class_ids if class_id not in targets_by_class]


def _build_target(class_id: str, value: dict[str, Any]) -> DisposalTarget:
    required = [
        "destination_title",
        "destination_type",
        "bin_color_name",
        "bin_color_hex",
        "asset_path",
        "search_query",
        "preparation_steps",
        "attention_note",
    ]
    missing = [key for key in required if key not in value]
    if missing:
        raise DisposalTargetError(
            f"Disposal target for {class_id} is missing fields: {', '.join(missing)}"
        )

    steps = value["preparation_steps"]
    if not isinstance(steps, list) or not steps:
        raise DisposalTargetError(f"Disposal target for {class_id} needs preparation steps.")

    return DisposalTarget(
        class_id=class_id,
        destination_title=str(value["destination_title"]),
        destination_type=str(value["destination_type"]),
        bin_color_name=str(value["bin_color_name"]),
        bin_color_hex=str(value["bin_color_hex"]),
        asset_path=str(value["asset_path"]),
        search_query=str(value["search_query"]),
        preparation_steps=tuple(str(step) for step in steps),
        attention_note=str(value["attention_note"]),
    )
