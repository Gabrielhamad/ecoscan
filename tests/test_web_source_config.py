from __future__ import annotations

import json
import unittest

from ecoscan.config import PROJECT_ROOT, load_config


class WebSourceConfigTests(unittest.TestCase):
    def test_web_source_config_covers_all_configured_classes(self) -> None:
        config = load_config()
        source_path = PROJECT_ROOT / "config" / "web_image_sources.json"
        sources = json.loads(source_path.read_text(encoding="utf-8"))

        self.assertEqual(set(config.classes), set(sources["classes"]))
        for class_id, source_config in sources["classes"].items():
            if isinstance(source_config, list):
                categories = source_config
                search_terms = []
            else:
                categories = source_config.get("categories", [])
                search_terms = source_config.get("search_terms", [])
            self.assertGreaterEqual(len(categories) + len(search_terms), 3, class_id)
            self.assertTrue(categories or search_terms, class_id)


if __name__ == "__main__":
    unittest.main()
