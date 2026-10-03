from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

from ecoscan.config import load_config
from ecoscan.services.acceptance_checks import (
    AcceptanceCheckReport, AcceptanceCheckResult, REQUIRED_CHECK_CODES,
    acceptance_exit_code, run_acceptance_checks,
)


class AcceptanceChecksTests(unittest.TestCase):
    def test_acceptance_checks_write_report_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = run_acceptance_checks(load_config(), output_dir=Path(temp_dir))

            self.assertIn("total", report.summary)
            self.assertGreaterEqual(report.summary["total"], 6)
            self.assertTrue((Path(temp_dir) / "acceptance_checks.md").exists())
            self.assertTrue((Path(temp_dir) / "acceptance_checks.csv").exists())
            self.assertTrue((Path(temp_dir) / "acceptance_checks.json").exists())
            self.assertEqual(REQUIRED_CHECK_CODES, {check.code for check in report.checks})
            payload = json.loads((Path(temp_dir) / "acceptance_checks.json").read_text(encoding="utf-8"))
            self.assertIn("code_revision", payload["release"])
            self.assertTrue(all("evidence_kind" in row for row in payload["checks"]))
            for check in report.checks:
                if check.code in {"QA-09", "QA-18", "QA-19", "QA-20", "QA-21"}:
                    self.assertEqual("pending", check.status)
                    self.assertEqual("manual_required", check.evidence_kind)

    def report(self, status="ok", codes=None):
        return AcceptanceCheckReport("test", {"ok": 999}, tuple(
            AcceptanceCheckResult(code, "test", status, "fixture", "test")
            for code in (sorted(REQUIRED_CHECK_CODES) if codes is None else codes)
        ))

    def test_strict_exit_requires_all_checks_ok(self):
        self.assertEqual(0, acceptance_exit_code(self.report()))
        for status in ("pending", "attention"):
            with self.subTest(status=status):
                self.assertEqual(2, acceptance_exit_code(self.report(status)))
                self.assertEqual(0, acceptance_exit_code(self.report(status), diagnostic=True))

    def test_missing_or_duplicate_checks_never_pass_strict_mode(self):
        for codes in ([], ["QA-01"], sorted(REQUIRED_CHECK_CODES) + ["QA-01"]):
            with self.subTest(codes=codes):
                self.assertEqual(2, acceptance_exit_code(self.report(codes=codes)))

    def test_failure_and_unknown_status_fail_even_in_diagnostic_mode(self):
        for status in ("failed", "typo"):
            for diagnostic in (True, False):
                self.assertEqual(1, acceptance_exit_code(self.report(status), diagnostic=diagnostic))

    def test_summary_cannot_override_actual_checks(self):
        self.assertEqual(2, acceptance_exit_code(self.report("pending")))

    def test_empty_diagnostic_is_not_success(self):
        self.assertEqual(2, acceptance_exit_code(self.report(codes=[]), diagnostic=True))


if __name__ == "__main__":
    unittest.main()
