from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from ecoscan.classification.baseline import NearestCentroidClassifier
from ecoscan.classification.inference import (
    load_baseline_model,
    load_visual_knn_model,
    load_visual_svm_model,
    predict_with_baseline,
    predict_with_visual_knn,
    predict_with_visual_svm,
)
from ecoscan.classification.visual_features import VisualFeatureConfig, extract_visual_features
from ecoscan.classification.visual_knn import VisualKnnClassifier
from ecoscan.classification.visual_svm import VisualSvmClassifier


class InferenceServiceTests(unittest.TestCase):
    def test_load_and_predict_with_baseline_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "baseline.json"
            classifier = NearestCentroidClassifier(
                classes=["dark", "light"],
                centroids=np.asarray([[0.0] * 32, [1.0] * 32], dtype=np.float32),
                threshold=0.5,
                softmax_temperature=0.2,
            )
            classifier.save(
                model_path,
                metadata={"feature_config": {"image_size": [16, 16], "histogram_bins": 8}},
            )

            bundle = load_baseline_model(model_path)
            image = np.full((24, 24, 3), 255, dtype=np.uint8)
            prediction = predict_with_baseline(image, bundle)

            self.assertIn(prediction.top_class_id, {"dark", "light"})
            self.assertGreaterEqual(prediction.probability, 0.0)
            self.assertLessEqual(prediction.probability, 1.0)

    def test_load_and_predict_with_visual_knn_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "visual.npz"
            feature_config = VisualFeatureConfig(image_size=(32, 32))
            dark_image = np.zeros((40, 40, 3), dtype=np.uint8)
            light_image = np.full((40, 40, 3), 255, dtype=np.uint8)
            features = np.vstack(
                [
                    extract_visual_features(dark_image, feature_config),
                    extract_visual_features(light_image, feature_config),
                ]
            )
            classifier = VisualKnnClassifier.fit(
                features,
                ["dark", "light"],
                classes=["dark", "light"],
                feature_config=feature_config,
                threshold=0.1,
                k_neighbors=1,
                distance_metric="cosine",
            )
            classifier.save(model_path)

            bundle = load_visual_knn_model(model_path)
            prediction = predict_with_visual_knn(light_image, bundle)

            self.assertEqual(prediction.top_class_id, "light")
            self.assertTrue(prediction.accepted)

    def test_load_and_predict_with_visual_svm_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "visual.joblib"
            feature_config = VisualFeatureConfig(image_size=(32, 32))
            dark_image = np.zeros((40, 40, 3), dtype=np.uint8)
            light_image = np.full((40, 40, 3), 255, dtype=np.uint8)
            features = np.vstack(
                [
                    extract_visual_features(dark_image, feature_config),
                    extract_visual_features(light_image, feature_config),
                    extract_visual_features(np.full((40, 40, 3), 220, dtype=np.uint8), feature_config),
                    extract_visual_features(np.full((40, 40, 3), 20, dtype=np.uint8), feature_config),
                ]
            )
            classifier = VisualSvmClassifier.fit(
                features,
                ["dark", "light", "light", "dark"],
                feature_config=feature_config,
                threshold=0.1,
            )
            classifier.save(model_path)

            bundle = load_visual_svm_model(model_path)
            prediction = predict_with_visual_svm(light_image, bundle)

            self.assertEqual(prediction.top_class_id, "light")
            self.assertTrue(prediction.accepted)


if __name__ == "__main__":
    unittest.main()
