import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ecoscan.services.acceptance_checks import AcceptanceCheckReport, AcceptanceCheckResult


SPEC = importlib.util.spec_from_file_location(
    "acceptance_cli", Path(__file__).resolve().parents[1] / "scripts/run_acceptance_checks.py"
)
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


class AcceptanceCliTests(unittest.TestCase):
    def run_command(self, status, *args):
        config = SimpleNamespace(directories={"logs": Path("unused"), "reports": Path("unused")})
        report = AcceptanceCheckReport("test", {status: 1}, (
            AcceptanceCheckResult("QA-01", "test", status, "fixture", "test"),
        ))
        with patch.object(cli, "load_config", return_value=config), \
             patch.object(cli, "configure_logging"), \
             patch.object(cli, "run_acceptance_checks", return_value=report), \
             patch("builtins.print"):
            return cli.main(list(args))

    def test_default_is_strict(self):
        self.assertEqual(2, self.run_command("pending"))

    def test_diagnostic_must_be_explicit(self):
        self.assertEqual(0, self.run_command("pending", "--diagnostic"))

    def test_diagnostic_still_reports_failures(self):
        self.assertEqual(1, self.run_command("failed", "--diagnostic"))


if __name__ == "__main__":
    unittest.main()
