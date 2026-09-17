from __future__ import annotations

import unittest

import numpy as np

from ecoscan.segmentation.methods import apply_mask, segment_image


class SegmentationTests(unittest.TestCase):
    def test_otsu_segmentation_returns_mask_and_segmented_image(self) -> None:
        image = np.zeros((80, 80, 3), dtype=np.uint8)
        image[20:60, 20:60] = [230, 230, 230]

        result = segment_image(image, "otsu")

        self.assertEqual(result.mask.shape, (80, 80))
        self.assertEqual(result.image.shape, image.shape)
        self.assertGreater(result.foreground_ratio, 0.0)
        self.assertLess(result.foreground_ratio, 1.0)

    def test_none_segmentation_keeps_full_image(self) -> None:
        image = np.full((32, 32, 3), 100, dtype=np.uint8)

        result = segment_image(image, "none")

        self.assertEqual(result.foreground_ratio, 1.0)
        np.testing.assert_array_equal(result.image, image)

    def test_hsv_color_segments_colored_region(self) -> None:
        image = np.full((60, 60, 3), [80, 80, 80], dtype=np.uint8)
        image[15:45, 15:45] = [220, 30, 30]

        result = segment_image(image, "hsv_color", {"saturation_min": 45, "value_min": 35})

        self.assertEqual(result.mask.shape, (60, 60))
        self.assertGreater(result.foreground_ratio, 0.1)
        self.assertLess(result.foreground_ratio, 0.4)
        self.assertIn(result.dependency, {"numpy", "opencv"})

    def test_apply_mask_sets_background_to_white(self) -> None:
        image = np.zeros((4, 4, 3), dtype=np.uint8)
        mask = np.zeros((4, 4), dtype=np.uint8)
        mask[1:3, 1:3] = 255

        result = apply_mask(image, mask)

        self.assertTrue(np.all(result[0, 0] == 255))
        self.assertTrue(np.all(result[1, 1] == 0))


if __name__ == "__main__":
    unittest.main()
