from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class EnvironmentalImpactError(ValueError):
    """Raised when environmental impact guidance cannot be loaded."""


@dataclass(frozen=True)
class EnvironmentalImpact:
    class_id: str
    impact_title: str
    risk_level: str
    risk_label: str
    bad_disposal_risks: tuple[str, ...]
    positive_action: str
    source_label: str
    source_url: str


def load_environmental_impacts(path: str | Path) -> dict[str, EnvironmentalImpact]:
    impact_path = Path(path).resolve()
    if not impact_path.exists():
        raise EnvironmentalImpactError(f"Environmental impact file not found: {impact_path}")

    with impact_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    impacts: dict[str, EnvironmentalImpact] = {}
    for class_id, value in raw.items():
        if not isinstance(value, dict):
            raise EnvironmentalImpactError(f"Invalid environmental impact for class: {class_id}")
        impacts[class_id] = _build_impact(class_id, value)
    return impacts


def get_environmental_impact(
    class_id: str,
    impacts_by_class: dict[str, EnvironmentalImpact],
) -> EnvironmentalImpact:
    try:
        return impacts_by_class[class_id]
    except KeyError as exc:
        raise EnvironmentalImpactError(
            f"Unknown class without environmental impact guidance: {class_id}"
        ) from exc


def missing_impacts_for_classes(
    class_ids: tuple[str, ...] | list[str],
    impacts_by_class: dict[str, EnvironmentalImpact],
) -> list[str]:
    return [class_id for class_id in class_ids if class_id not in impacts_by_class]


def _build_impact(class_id: str, value: dict[str, Any]) -> EnvironmentalImpact:
    required = [
        "impact_title",
        "risk_level",
        "risk_label",
        "bad_disposal_risks",
        "positive_action",
        "source_label",
        "source_url",
    ]
    missing = [key for key in required if key not in value]
    if missing:
        raise EnvironmentalImpactError(
            f"Environmental impact for {class_id} is missing fields: {', '.join(missing)}"
        )

    risks = value["bad_disposal_risks"]
    if not isinstance(risks, list) or len(risks) < 2:
        raise EnvironmentalImpactError(
            f"Environmental impact for {class_id} needs at least two risks."
        )

    return EnvironmentalImpact(
        class_id=class_id,
        impact_title=str(value["impact_title"]),
        risk_level=str(value["risk_level"]),
        risk_label=str(value["risk_label"]),
        bad_disposal_risks=tuple(str(risk) for risk in risks),
        positive_action=str(value["positive_action"]),
        source_label=str(value["source_label"]),
        source_url=str(value["source_url"]),
    )
