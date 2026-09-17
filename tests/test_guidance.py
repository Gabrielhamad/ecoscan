from __future__ import annotations

import unittest

from ecoscan.config import PROJECT_ROOT
from ecoscan.disposal.guidance import get_guidance, load_guidance


class GuidanceTests(unittest.TestCase):
    def test_guidance_is_loaded_separately_from_model(self) -> None:
        guidance = load_guidance(PROJECT_ROOT / "config" / "disposal_guidance.json")

        battery = get_guidance("battery", guidance)
        self.assertEqual(battery.environmental_category, "Resíduo especial")
        self.assertFalse(battery.common_trash)
        self.assertIn("ponto de coleta", battery.guidance)


if __name__ == "__main__":
    unittest.main()

