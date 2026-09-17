from __future__ import annotations

import unittest

from ecoscan.config import PROJECT_ROOT, load_config
from ecoscan.disposal.targets import (
    build_map_search_url,
    get_disposal_target,
    load_disposal_targets,
    missing_targets_for_classes,
)


class DisposalTargetTests(unittest.TestCase):
    def test_targets_cover_active_classes(self) -> None:
        config = load_config()
        targets = load_disposal_targets(PROJECT_ROOT / "config" / "disposal_targets.json")

        self.assertEqual([], missing_targets_for_classes(config.classes, targets))
        for class_id in config.classes:
            self.assertTrue(targets[class_id].asset_absolute_path(PROJECT_ROOT).exists())

    def test_target_contains_visual_and_search_metadata(self) -> None:
        targets = load_disposal_targets(PROJECT_ROOT / "config" / "disposal_targets.json")
        battery = get_disposal_target("battery", targets)

        self.assertEqual("Laranja", battery.bin_color_name)
        self.assertIn("pilhas", battery.search_query)
        self.assertTrue(battery.asset_path.endswith(".png"))
        self.assertGreaterEqual(len(battery.preparation_steps), 3)

    def test_map_search_url_encodes_query_and_location(self) -> None:
        url = build_map_search_url("ponto de coleta pilhas baterias", "São Paulo SP")

        self.assertTrue(url.startswith("https://www.google.com/maps/search/?api=1&query="))
        self.assertIn("ponto+de+coleta+pilhas+baterias", url)
        self.assertIn("S%C3%A3o+Paulo+SP", url)


if __name__ == "__main__":
    unittest.main()
