from __future__ import annotations

import json
import unittest

from ecoscan.config import PROJECT_ROOT, load_config


class OpenverseSourceConfigTests(unittest.TestCase):
    def test_openverse_source_config_covers_all_configured_classes(self) -> None:
        config = load_config()
        source_path = PROJECT_ROOT / "config" / "openverse_image_sources.json"
        sources = json.loads(source_path.read_text(encoding="utf-8"))

        self.assertEqual(set(config.classes), set(sources["classes"]))
        for class_id, queries in sources["classes"].items():
            self.assertGreaterEqual(len(queries), 3, class_id)


if __name__ == "__main__":
    unittest.main()
