from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ecoscan.config import load_config
from ecoscan.services.diagnostics import dataset_status, dependency_status, model_status, write_diagnostics_report


class DiagnosticsTests(unittest.TestCase):
    def test_diagnostics_report_is_written(self) -> None:
        config = load_config()
        with tempfile.TemporaryDirectory() as tmp:
            output = write_diagnostics_report(config, Path(tmp) / "diagnostics.json")

            self.assertTrue(output.exists())
            self.assertTrue(dependency_status())
            self.assertIn("raw_counts", dataset_status(config).__dict__)
            self.assertIn(model_status(config).selected_kind, {"baseline", "visual_svm", "visual_knn", "transfer_learning", "none"})


if __name__ == "__main__":
    unittest.main()
