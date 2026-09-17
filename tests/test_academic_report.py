from __future__ import annotations

import unittest

from ecoscan.config import load_config
from ecoscan.services.academic_report import build_academic_report, write_academic_report


class AcademicReportTests(unittest.TestCase):
    def test_academic_report_contains_required_sections(self) -> None:
        report = build_academic_report(load_config())

        self.assertIn("## 1. Problema", report)
        self.assertIn("## 7. Processamento digital de imagens", report)
        self.assertIn("## 8. Segmentação", report)
        self.assertIn("## 10. Avaliação", report)

    def test_academic_report_is_written(self) -> None:
        path = write_academic_report(load_config())

        self.assertTrue(path.exists())
        self.assertIn("EcoScan", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
