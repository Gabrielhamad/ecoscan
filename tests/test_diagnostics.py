from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from dataclasses import replace

from ecoscan.config import load_config
from ecoscan.services.diagnostics import dataset_status, dependency_status, model_status, write_diagnostics_report
from ecoscan.services.analysis_service import _model_path


class DiagnosticsTests(unittest.TestCase):
    def test_model_priority_matches_real_analysis_for_each_available_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = replace(load_config(), project_root=root,
                             directories={"models": root}, model={"output_path": "final.keras"})
            self.assertEqual("none", model_status(config).selected_kind)
            for name, kind in (
                ("baseline_classifier.json", "baseline"),
                ("vision_classifier.npz", "visual_knn"),
                ("vision_svm_classifier.joblib", "visual_svm"),
                ("final.keras", "transfer_learning"),
            ):
                (root / name).touch()
                with self.subTest(kind=kind):
                    self.assertEqual(kind, model_status(config).selected_kind)
                    self.assertEqual(_model_path(config, None), Path(model_status(config).selected_path))

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
