from __future__ import annotations

import unittest

import numpy as np

from ecoscan.image_processing.capture_quality import assess_capture_quality
from ecoscan.image_processing.quality import analyze_image_quality
from ecoscan.segmentation.elements import analyze_visual_elements


class CaptureQualityTests(unittest.TestCase):
    def test_good_capture_receives_good_status(self) -> None:
        y, x = np.indices((96, 96))
        image = np.full((96, 96, 3), [60, 72, 68], dtype=np.uint8)
        object_texture = np.where((x[24:72, 24:72] + y[24:72, 24:72]) % 8 < 4, 218, 242)
        image[24:72, 24:72, 0] = object_texture
        image[24:72, 24:72, 1] = 196
        image[24:72, 24:72, 2] = 82
        metrics = analyze_image_quality(image)
        mask = np.zeros((96, 96), dtype=np.uint8)
        mask[24:72, 24:72] = 255
        elements = analyze_visual_elements(mask)

        assessment = assess_capture_quality(metrics, metrics, elements)

        self.assertEqual(assessment.status, "good")
        self.assertGreaterEqual(assessment.score, 82)

    def test_blurry_or_empty_capture_requests_retake(self) -> None:
        image = np.full((96, 96, 3), 25, dtype=np.uint8)
        metrics = analyze_image_quality(image)
        mask = np.zeros((96, 96), dtype=np.uint8)
        elements = analyze_visual_elements(mask)

        assessment = assess_capture_quality(metrics, metrics, elements)

        self.assertEqual(assessment.status, "retake")
        self.assertTrue(assessment.actions)
        self.assertLess(assessment.score, 55)


if __name__ == "__main__":
    unittest.main()
