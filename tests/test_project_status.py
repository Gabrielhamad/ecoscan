from __future__ import annotations

import unittest

from ecoscan.config import load_config
from ecoscan.services.project_status import build_project_status, format_status_markdown


class ProjectStatusTests(unittest.TestCase):
    def test_project_status_contains_final_model_item(self) -> None:
        items = build_project_status(load_config())
        markdown = format_status_markdown(items)

        self.assertIn("modelo final transfer learning", markdown)
        self.assertIn("detecção múltipla", markdown)


if __name__ == "__main__":
    unittest.main()

