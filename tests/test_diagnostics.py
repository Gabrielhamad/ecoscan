from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from ecoscan.config import load_config
from ecoscan.services.diagnostics import (
    dataset_status,
    dependency_status,
    model_status,
    write_diagnostics_report,
)
from ecoscan.services.analysis_service import _model_path


class DiagnosticsTests(unittest.TestCase):
    def test_model_status_matches_the_configured_current_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_path = root / "models" / "semantic-v1" / "semantic.json"
            config = replace(
                load_config(),
                project_root=root,
                directories={"models": root / "models"},
            )
            self.assertEqual("none", model_status(config).selected_kind)
            model_path.parent.mkdir(parents=True)
            model_path.touch()
            self.assertEqual("semantic_onnx_assisted", model_status(config).selected_kind)
            self.assertEqual(_model_path(config, None), Path(model_status(config).selected_path))

    def test_diagnostics_report_is_written(self) -> None:
        config = load_config()
        with tempfile.TemporaryDirectory() as tmp:
            output = write_diagnostics_report(config, Path(tmp) / "diagnostics.json")

            self.assertTrue(output.exists())
            self.assertTrue(dependency_status())
            self.assertIn("raw_counts", dataset_status(config).__dict__)
            self.assertIn(model_status(config).selected_kind, {"semantic_onnx_assisted", "none"})


if __name__ == "__main__":
    unittest.main()
