from __future__ import annotations

import unittest

import numpy as np

from ecoscan.segmentation.adaptive import segment_image_adaptive


class AdaptiveSegmentationTests(unittest.TestCase):
    def test_adaptive_segmentation_records_decision(self) -> None:
        image = np.full((80, 80, 3), [70, 70, 70], dtype=np.uint8)
        image[20:60, 20:60] = [220, 30, 30]

        result = segment_image_adaptive(image)

        self.assertIn(result.segmentation.name, {"otsu", "hsv_color", "grabcut"})
        self.assertEqual(result.decision["requested"], "auto")
        self.assertEqual(result.decision["selected"], result.segmentation.name)
        self.assertGreaterEqual(len(result.decision["candidates"]), 2)
        self.assertIn("reason", result.decision)

    def test_adaptive_segmentation_falls_back_to_available_method(self) -> None:
        image = np.zeros((48, 48, 3), dtype=np.uint8)
        image[12:36, 12:36] = [235, 235, 235]

        result = segment_image_adaptive(image, {"candidate_methods": ["grabcut", "otsu"]})

        self.assertIn(result.segmentation.name, {"grabcut", "otsu"})
        self.assertEqual(result.decision["requested"], "auto")
        self.assertTrue(result.decision["candidates"])


if __name__ == "__main__":
    unittest.main()
