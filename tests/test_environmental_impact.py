from __future__ import annotations

import unittest

from ecoscan.config import PROJECT_ROOT, load_config
from ecoscan.disposal.impact import (
    get_environmental_impact,
    load_environmental_impacts,
    missing_impacts_for_classes,
)


class EnvironmentalImpactTests(unittest.TestCase):
    def test_impacts_cover_active_classes(self) -> None:
        config = load_config()
        impacts = load_environmental_impacts(PROJECT_ROOT / "config" / "environmental_impacts.json")

        self.assertEqual([], missing_impacts_for_classes(config.classes, impacts))

    def test_special_waste_contains_risks_and_source(self) -> None:
        impacts = load_environmental_impacts(PROJECT_ROOT / "config" / "environmental_impacts.json")
        battery = get_environmental_impact("battery", impacts)

        self.assertEqual("alto", battery.risk_level)
        self.assertGreaterEqual(len(battery.bad_disposal_risks), 2)
        self.assertIn("logística reversa", battery.source_label)
        self.assertTrue(battery.source_url.startswith("https://"))


if __name__ == "__main__":
    unittest.main()
