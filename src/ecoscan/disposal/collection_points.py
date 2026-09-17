from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus


class CollectionPointError(ValueError):
    """Raised when collection point data cannot be loaded."""


@dataclass(frozen=True)
class CollectionPoint:
    point_id: str
    name: str
    city: str
    state: str
    address: str
    neighborhood: str
    hours: str
    accepted_classes: tuple[str, ...]
    accepted_materials: tuple[str, ...]
    limit_note: str
    notes: str
    source_label: str
    source_url: str
    latitude: float | None = None
    longitude: float | None = None

    @property
    def full_address(self) -> str:
        parts = [self.address, self.neighborhood, self.city, self.state]
        return ", ".join(part for part in parts if part)

    def accepts(self, class_id: str) -> bool:
        return class_id in self.accepted_classes


@dataclass(frozen=True)
class RankedCollectionPoint:
    point: CollectionPoint
    distance_km: float | None


def load_collection_points(path: str | Path) -> list[CollectionPoint]:
    points_path = Path(path).resolve()
    if not points_path.exists():
        raise CollectionPointError(f"Collection point file not found: {points_path}")

    with points_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    metadata = raw.get("metadata", {})
    rows = raw.get("points", [])
    if not isinstance(rows, list):
        raise CollectionPointError("collection_points.json field 'points' must be a list.")
    return [_build_point(row, metadata) for row in rows]


def filter_collection_points(
    points: list[CollectionPoint],
    *,
    class_id: str | None = None,
    city_query: str | None = None,
) -> list[CollectionPoint]:
    city = city_query.lower().strip() if city_query else ""
    filtered: list[CollectionPoint] = []
    for point in points:
        if class_id and not point.accepts(class_id):
            continue
        if city and city not in f"{point.city} {point.state} {point.neighborhood} {point.address}".lower():
            continue
        filtered.append(point)
    return filtered


def rank_collection_points(
    points: list[CollectionPoint],
    *,
    user_latitude: float | None = None,
    user_longitude: float | None = None,
    limit: int = 5,
) -> list[RankedCollectionPoint]:
    ranked = [
        RankedCollectionPoint(
            point=point,
            distance_km=_distance_km(user_latitude, user_longitude, point.latitude, point.longitude),
        )
        for point in points
    ]
    ranked.sort(key=lambda item: (item.distance_km is None, item.distance_km or math.inf, item.point.name))
    return ranked[:limit]


def build_collection_point_map_url(point: CollectionPoint) -> str:
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(point.full_address)


def build_collection_point_directions_url(
    point: CollectionPoint,
    *,
    origin: str | None = None,
) -> str:
    url = "https://www.google.com/maps/dir/?api=1"
    destination = quote_plus(point.full_address)
    if origin and origin.strip():
        return f"{url}&origin={quote_plus(origin.strip())}&destination={destination}"
    return f"{url}&destination={destination}"


def _build_point(value: dict[str, Any], metadata: dict[str, Any]) -> CollectionPoint:
    required = [
        "point_id",
        "name",
        "city",
        "state",
        "address",
        "neighborhood",
        "hours",
        "accepted_classes",
        "accepted_materials",
        "limit_note",
        "notes",
    ]
    missing = [key for key in required if key not in value]
    if missing:
        raise CollectionPointError(
            "Collection point is missing fields: " + ", ".join(missing)
        )
    accepted_classes = value["accepted_classes"]
    accepted_materials = value["accepted_materials"]
    if not isinstance(accepted_classes, list) or not accepted_classes:
        raise CollectionPointError(f"Point {value.get('point_id')} needs accepted_classes.")
    if not isinstance(accepted_materials, list) or not accepted_materials:
        raise CollectionPointError(f"Point {value.get('point_id')} needs accepted_materials.")

    latitude = _optional_float(value.get("latitude"))
    longitude = _optional_float(value.get("longitude"))
    return CollectionPoint(
        point_id=str(value["point_id"]),
        name=str(value["name"]),
        city=str(value["city"]),
        state=str(value["state"]),
        address=str(value["address"]),
        neighborhood=str(value["neighborhood"]),
        hours=str(value["hours"]),
        accepted_classes=tuple(str(item) for item in accepted_classes),
        accepted_materials=tuple(str(item) for item in accepted_materials),
        limit_note=str(value["limit_note"]),
        notes=str(value["notes"]),
        source_label=str(value.get("source_label") or metadata.get("source_label") or ""),
        source_url=str(value.get("source_url") or metadata.get("source_url") or ""),
        latitude=latitude,
        longitude=longitude,
    )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _distance_km(
    user_latitude: float | None,
    user_longitude: float | None,
    point_latitude: float | None,
    point_longitude: float | None,
) -> float | None:
    if None in {user_latitude, user_longitude, point_latitude, point_longitude}:
        return None
    assert user_latitude is not None
    assert user_longitude is not None
    assert point_latitude is not None
    assert point_longitude is not None
    radius_km = 6371.0
    user_lat = math.radians(user_latitude)
    user_lon = math.radians(user_longitude)
    point_lat = math.radians(point_latitude)
    point_lon = math.radians(point_longitude)
    delta_lat = point_lat - user_lat
    delta_lon = point_lon - user_lon
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(user_lat) * math.cos(point_lat) * math.sin(delta_lon / 2) ** 2
    )
    return round(radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)
