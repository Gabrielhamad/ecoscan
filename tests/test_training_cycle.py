import json
import tempfile
import unittest
from pathlib import Path

from scripts.train_recognition_cycle import _guard_candidate_output, _guard_rebuild, _image_count, build_parser
from ecoscan.config import load_config


class TrainingCycleTests(unittest.TestCase):
    def test_candidate_is_the_safe_default(self):
        args = build_parser().parse_args([])
        self.assertTrue(str(args.output_model).endswith("vision_svm_classifier_candidate.joblib"))
        self.assertEqual(args.threshold, 0.25)
        self.assertFalse(args.overwrite)

    def test_active_model_paths_are_protected(self):
        config = load_config()
        with self.assertRaises(ValueError):
            _guard_candidate_output(config, config.directories["models"] / "vision_svm_classifier.joblib")
        _guard_candidate_output(config, config.directories["models"] / "vision_svm_classifier_candidate.joblib")

    def test_counts_only_configured_extensions_and_classes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "metal").mkdir()
            (root / "metal" / "a.png").write_bytes(b"x")
            (root / "metal" / "notes.txt").write_text("x")
            (root / "legacy").mkdir()
            (root / "legacy" / "b.png").write_bytes(b"x")
            self.assertEqual(_image_count(root, ("metal",), frozenset({".png"})), {"metal": 1})

    def test_existing_outputs_require_explicit_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "processed"
            output.mkdir()
            (output / "old.png").write_bytes(b"old")
            config = type("Config", (), {"directories": {"processed_data": output,
                "train_data": root / "train", "validation_data": root / "validation",
                "test_data": root / "test"}})()
            with self.assertRaises(RuntimeError):
                _guard_rebuild(config, False)
            _guard_rebuild(config, True)
