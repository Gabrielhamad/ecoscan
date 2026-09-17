from __future__ import annotations

import unittest

import numpy as np

from ecoscan.classification.baseline import NearestCentroidClassifier
from ecoscan.classification.features import FeatureConfig, extract_features, feature_size


class BaselineTests(unittest.TestCase):
    def test_feature_size_matches_extraction(self) -> None:
        config = FeatureConfig(image_size=(32, 32), histogram_bins=4)
        image = np.zeros((40, 50, 3), dtype=np.uint8)

        features = extract_features(image, config)

        self.assertEqual(features.shape, (feature_size(config),))

    def test_nearest_centroid_can_reject_low_probability(self) -> None:
        features = np.asarray([[0.0, 0.0], [1.0, 1.0]], dtype=np.float32)
        labels = ["a", "b"]
        classifier = NearestCentroidClassifier.fit(features, labels, threshold=0.9)

        prediction = classifier.predict(np.asarray([0.5, 0.5], dtype=np.float32))

        self.assertFalse(prediction.accepted)
        self.assertIsNone(prediction.class_id)


if __name__ == "__main__":
    unittest.main()

