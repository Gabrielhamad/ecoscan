from __future__ import annotations

import unittest

from ecoscan.config import PROJECT_ROOT, load_config
from ecoscan.services.photo_requirements import (
    load_photo_requirements,
    missing_requirements_for_classes,
)


class PhotoRequirementTests(unittest.TestCase):
    def test_requirements_cover_active_classes(self) -> None:
        config = load_config()
        requirements = load_photo_requirements(PROJECT_ROOT / "config" / "photo_requirements.json")

        self.assertEqual([], missing_requirements_for_classes(config.classes, requirements))

    def test_requirement_has_enough_guidance(self) -> None:
        requirements = load_photo_requirements(PROJECT_ROOT / "config" / "photo_requirements.json")
        electronic = requirements["electronic"]

        self.assertGreaterEqual(electronic.minimum_images, 50)
        self.assertGreaterEqual(len(electronic.examples), 5)
        self.assertGreaterEqual(len(electronic.contexts), 3)
        self.assertGreaterEqual(len(electronic.avoid), 3)


if __name__ == "__main__":
    unittest.main()
