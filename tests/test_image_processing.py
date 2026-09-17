from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from ecoscan.image_processing.filters import apply_filter
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.image_processing.preprocessing import prepare_model_input, resize_image
from ecoscan.image_processing.validation import ImageValidationError


class ImageProcessingTests(unittest.TestCase):
    def test_load_rgb_image_validates_and_converts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.png"
            Image.new("L", (80, 90), 120).save(path)

            loaded = load_rgb_image(
                path,
                allowed_extensions=frozenset({".png"}),
                min_size=(64, 64),
            )

            self.assertEqual(loaded.array.shape, (90, 80, 3))
            self.assertEqual(loaded.array.dtype, np.uint8)

    def test_load_rgb_image_rejects_small_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "small.png"
            Image.new("RGB", (32, 32), "white").save(path)

            with self.assertRaises(ImageValidationError):
                load_rgb_image(path, allowed_extensions=frozenset({".png"}), min_size=(64, 64))

    def test_resize_and_model_input_shape(self) -> None:
        image = np.zeros((80, 120, 3), dtype=np.uint8)

        resized = resize_image(image, (224, 224))
        prepared = prepare_model_input(image, (224, 224))

        self.assertEqual(resized.shape, (224, 224, 3))
        self.assertEqual(prepared.model_input.shape, (1, 224, 224, 3))
        self.assertGreaterEqual(prepared.normalized.min(), 0.0)
        self.assertLessEqual(prepared.normalized.max(), 1.0)

    def test_filters_return_same_shape(self) -> None:
        image = np.zeros((64, 64, 3), dtype=np.uint8)
        image[16:48, 16:48] = [240, 240, 240]

        for filter_name in ["none", "gaussian", "median", "clahe", "sobel", "canny"]:
            result = apply_filter(image, filter_name, {})
            self.assertEqual(result.image.shape, image.shape, filter_name)
            self.assertEqual(result.image.dtype, np.uint8, filter_name)


if __name__ == "__main__":
    unittest.main()

