from __future__ import annotations

import unittest

import numpy as np

from ecoscan.config import load_config
from ecoscan.image_processing.adaptive_filters import apply_adaptive_filter_pipeline
from ecoscan.image_processing.quality import analyze_image_quality


class AdaptiveFilterTests(unittest.TestCase):
    def test_low_contrast_does_not_force_clahe_without_measurable_gain(self) -> None:
        gradient = np.tile(np.linspace(92, 118, 80, dtype=np.uint8), (80, 1))
        image = np.repeat(gradient[..., None], 3, axis=2)
        config = load_config()

        result = apply_adaptive_filter_pipeline(
            image,
            config.filters,
            quality=analyze_image_quality(image),
        )

        self.assertIn("clahe", [row["sequence"] for row in result.decision["candidates"]])
        self.assertEqual(result.decision["selected_sequence"], ["none"])
        np.testing.assert_array_equal(result.filter_result.image, image)
        self.assertEqual(result.filter_result.image.shape, image.shape)
        self.assertEqual(result.filter_result.image.dtype, np.uint8)
        self.assertGreaterEqual(len(result.decision["candidates"]), 2)

    def test_adaptive_filter_uses_only_enhancement_filters(self) -> None:
        image = np.zeros((72, 72, 3), dtype=np.uint8)
        image[:, ::2] = 255
        config = load_config()

        result = apply_adaptive_filter_pipeline(
            image,
            config.filters,
            quality=analyze_image_quality(image),
        )

        selected_sequence = set(result.decision["selected_sequence"])
        self.assertFalse({"sobel", "canny"} & selected_sequence)
        self.assertIn("selected", result.decision)
        self.assertIn("score", result.filter_result.parameters)


if __name__ == "__main__":
    unittest.main()
