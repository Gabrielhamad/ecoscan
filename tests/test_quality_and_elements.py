from __future__ import annotations

import unittest

import numpy as np

from ecoscan.image_processing.quality import analyze_image_quality, recommend_filter_name
from ecoscan.segmentation.elements import analyze_visual_elements, draw_detection_heatmap, draw_element_overlay


class QualityAndElementsTests(unittest.TestCase):
    def test_quality_detects_underexposed_image(self) -> None:
        image = np.full((64, 64, 3), 20, dtype=np.uint8)

        metrics = analyze_image_quality(image)
        filter_name, reason = recommend_filter_name(metrics)

        self.assertEqual(metrics.exposure_status, "underexposed")
        self.assertEqual(filter_name, "clahe")
        self.assertIn("exposição", reason)

    def test_visual_elements_detects_significant_components(self) -> None:
        mask = np.zeros((80, 80), dtype=np.uint8)
        mask[10:30, 10:30] = 255
        mask[45:70, 50:75] = 255

        analysis = analyze_visual_elements(mask, min_area_ratio=0.01)

        self.assertEqual(analysis.significant_count, 2)
        self.assertTrue(analysis.likely_multi_object)
        self.assertGreater(analysis.foreground_ratio, 0.0)

    def test_element_overlay_keeps_image_shape(self) -> None:
        image = np.zeros((80, 80, 3), dtype=np.uint8)
        mask = np.zeros((80, 80), dtype=np.uint8)
        mask[20:60, 20:60] = 255
        analysis = analyze_visual_elements(mask)

        overlay = draw_element_overlay(image, analysis)

        self.assertEqual(overlay.shape, image.shape)
        self.assertEqual(overlay.dtype, np.uint8)

    def test_detection_heatmap_keeps_image_shape(self) -> None:
        image = np.full((80, 80, 3), 120, dtype=np.uint8)
        mask = np.zeros((80, 80), dtype=np.uint8)
        mask[20:60, 20:60] = 255
        analysis = analyze_visual_elements(mask)

        heatmap = draw_detection_heatmap(image, mask, analysis)

        self.assertEqual(heatmap.shape, image.shape)
        self.assertEqual(heatmap.dtype, np.uint8)
        self.assertGreater(float(heatmap[40, 40, 0]), float(image[40, 40, 0]))


if __name__ == "__main__":
    unittest.main()
