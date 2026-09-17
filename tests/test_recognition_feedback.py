from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from ecoscan.config import AppConfig
from ecoscan.services.recognition_feedback import (
    append_recognition_feedback,
    feedback_manifest_path_from_config,
    read_recognition_feedback,
)


class RecognitionFeedbackTests(unittest.TestCase):
    def test_append_recognition_feedback_writes_manifest_and_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = AppConfig(
                project_root=root,
                config_path=root / "settings.json",
                project_name="EcoScan",
                image_size=(224, 224),
                confidence_threshold=0.65,
                random_seed=42,
                allowed_extensions=frozenset({".jpg", ".png"}),
                min_image_size=(48, 48),
                min_images_per_class_warning=20,
                imbalance_ratio_warning=2.0,
                classes=("plastic", "metal", "glass"),
                directories={"reports": root / "reports"},
                dataset_split={"train": 0.7, "validation": 0.15, "test": 0.15},
                baseline={},
                model={},
                history={},
                filters={},
                segmentation={},
            )
            result = SimpleNamespace(
                predicted_class="glass",
                top_class="glass",
                probability=0.31,
                accepted=True,
                model_type="visual_knn",
                pipeline=SimpleNamespace(
                    loaded=SimpleNamespace(array=np.full((32, 32, 3), 128, dtype=np.uint8)),
                    filter_result=SimpleNamespace(name="bilateral"),
                    segmentation_result=SimpleNamespace(name="grabcut"),
                ),
            )

            feedback = append_recognition_feedback(
                config,
                result,
                expected_class="metal",
                reporter_id="usuario_demo",
                reporter_name="Colega",
                source_kind="upload",
                note="Era uma lata.",
            )

            manifest = feedback_manifest_path_from_config(config)
            self.assertTrue(manifest.exists())
            self.assertTrue(Path(feedback.image_path).exists())
            manifest_text = manifest.read_text(encoding="utf-8")
            self.assertIn("expected_class", manifest_text)
            self.assertIn("metal", manifest_text)
            self.assertIn("Era uma lata.", manifest_text)
            read_back = read_recognition_feedback(manifest)
            self.assertEqual(1, len(read_back))
            self.assertEqual("metal", read_back[0].expected_class)
            self.assertEqual("glass", read_back[0].predicted_class)


if __name__ == "__main__":
    unittest.main()
