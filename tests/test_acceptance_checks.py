from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ecoscan.config import load_config
from ecoscan.services.acceptance_checks import run_acceptance_checks


class AcceptanceChecksTests(unittest.TestCase):
    def test_acceptance_checks_write_report_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = run_acceptance_checks(load_config(), output_dir=Path(temp_dir))

            self.assertIn("total", report.summary)
            self.assertGreaterEqual(report.summary["total"], 6)
            self.assertTrue((Path(temp_dir) / "acceptance_checks.md").exists())
            self.assertTrue((Path(temp_dir) / "acceptance_checks.csv").exists())
            self.assertTrue((Path(temp_dir) / "acceptance_checks.json").exists())


if __name__ == "__main__":
    unittest.main()
