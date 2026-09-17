from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ecoscan.config import ConfigError, load_config


class ConfigTests(unittest.TestCase):
    def test_load_default_config(self) -> None:
        config = load_config()

        self.assertEqual(config.project_name, "EcoScan")
        self.assertEqual(config.image_size, (224, 224))
        self.assertIn("battery", config.classes)
        self.assertIn(".png", config.allowed_extensions)
        self.assertTrue(config.directories["raw_data"].is_absolute())
        self.assertEqual(config.model["architecture"], "MobileNetV2")
        self.assertTrue(config.history["enabled"])

    def test_reject_duplicate_classes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_dir = tmp_path / "config"
            config_dir.mkdir()
            settings = {
                "classes": ["plastic", "plastic"],
                "allowed_extensions": [".png"],
                "image_size": [224, 224],
                "confidence_threshold": 0.65,
                "min_image_size": [64, 64],
                "directories": {},
            }
            config_path = config_dir / "settings.json"
            config_path.write_text(json.dumps(settings), encoding="utf-8")

            with self.assertRaises(ConfigError):
                load_config(config_path)


if __name__ == "__main__":
    unittest.main()
