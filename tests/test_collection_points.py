from __future__ import annotations

import unittest

from ecoscan.config import PROJECT_ROOT
from ecoscan.disposal.collection_points import (
    CollectionPoint,
    build_collection_point_directions_url,
    build_collection_point_map_url,
    filter_collection_points,
    load_collection_points,
    rank_collection_points,
)


class CollectionPointTests(unittest.TestCase):
    def test_loads_official_initial_points(self) -> None:
        points = load_collection_points(PROJECT_ROOT / "config" / "collection_points.json")

        self.assertGreaterEqual(len(points), 20)
        self.assertIn("São Paulo", {point.city for point in points})
        self.assertIn("Ribeirão Preto", {point.city for point in points})
        self.assertTrue(all(point.source_url.startswith("https://") for point in points))

    def test_filters_points_by_class(self) -> None:
        points = load_collection_points(PROJECT_ROOT / "config" / "collection_points.json")
        battery_points = filter_collection_points(points, class_id="battery")
        organic_points = filter_collection_points(points, class_id="organic")
        sao_paulo_metal_points = filter_collection_points(points, class_id="metal", city_query="São Paulo")

        self.assertEqual(8, len(battery_points))
        self.assertGreaterEqual(len(sao_paulo_metal_points), 10)
        self.assertEqual([], organic_points)

    def test_builds_map_and_directions_urls(self) -> None:
        point = load_collection_points(PROJECT_ROOT / "config" / "collection_points.json")[0]

        self.assertIn("google.com/maps/search", build_collection_point_map_url(point))
        self.assertIn("destination=", build_collection_point_directions_url(point))
        self.assertIn("origin=", build_collection_point_directions_url(point, origin="Centro"))

    def test_ranks_by_distance_when_coordinates_exist(self) -> None:
        far = CollectionPoint(
            point_id="far",
            name="Ponto longe",
            city="Teste",
            state="SP",
            address="Rua B",
            neighborhood="Bairro B",
            hours="7h às 19h",
            accepted_classes=("plastic",),
            accepted_materials=("recicláveis",),
            limit_note="",
            notes="",
            source_label="teste",
            source_url="https://example.com",
            latitude=-23.0,
            longitude=-47.0,
        )
        near = CollectionPoint(
            point_id="near",
            name="Ponto perto",
            city="Teste",
            state="SP",
            address="Rua A",
            neighborhood="Bairro A",
            hours="7h às 19h",
            accepted_classes=("plastic",),
            accepted_materials=("recicláveis",),
            limit_note="",
            notes="",
            source_label="teste",
            source_url="https://example.com",
            latitude=-22.0,
            longitude=-47.0,
        )

        ranked = rank_collection_points([far, near], user_latitude=-22.01, user_longitude=-47.0)

        self.assertEqual("near", ranked[0].point.point_id)
        self.assertIsNotNone(ranked[0].distance_km)


if __name__ == "__main__":
    unittest.main()
