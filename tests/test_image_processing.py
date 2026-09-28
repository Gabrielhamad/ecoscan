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

    def test_exif_orientation_is_corrected_before_resize(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "camera.jpg"
            image = Image.new("RGB", (80, 64), (20, 40, 60))
            exif = image.getexif()
            exif[274] = 6  # Camera rotated 90 degrees clockwise.
            image.save(path, exif=exif)
            loaded = load_rgb_image(path, allowed_extensions=frozenset({".jpg"}), min_size=(48,48))
            self.assertEqual(loaded.array.shape, (80, 64, 3))
            prepared = prepare_model_input(loaded.array, (32, 40))
            self.assertEqual(prepared.resized.shape, (40, 32, 3))
            self.assertEqual(prepared.normalized.dtype, np.float32)

    def test_grayscale_luminance_and_legacy_resize_contract(self):
        from ecoscan.image_processing.preprocessing import to_grayscale
        pixels = np.array([[[255, 0, 0], [0, 255, 0], [0, 0, 255]]], dtype=np.uint8)
        np.testing.assert_array_equal(to_grayscale(pixels), [[76, 149, 29]])
        rgb = np.random.default_rng(42).integers(0, 256, (20, 30, 3), dtype=np.uint8)
        # Pillow's previous RGB default was BICUBIC; do not silently change model inputs.
        expected = np.asarray(Image.fromarray(rgb).resize((16, 16)))
        np.testing.assert_array_equal(resize_image(rgb, (16, 16)), expected)


if __name__ == "__main__":
    unittest.main()

