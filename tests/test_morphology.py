import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from ecoscan.app.pipeline import ProcessingPipelineOptions, run_processing_pipeline
from ecoscan.config import load_config
from ecoscan.segmentation.morphology import apply_morphology, structuring_element
from ecoscan.segmentation.methods import apply_mask
from ecoscan.services.visual_report import save_pipeline_artifacts


class MorphologyTests(unittest.TestCase):
    def test_single_pixel_expands_to_footprint_without_mutating_input(self):
        mask = np.zeros((9, 9), dtype=np.uint8)
        mask[4, 4] = 255
        before = mask.copy()
        for shape, count in (("square", 9), ("cross", 5), ("disk", 5)):
            result = apply_morphology(mask, "dilation", kernel_shape=shape)
            self.assertEqual(np.count_nonzero(result.mask), count)
            np.testing.assert_array_equal(result.mask[3:6, 3:6], structuring_element(3, shape) * 255)
        np.testing.assert_array_equal(before, mask)

    def test_erosion_shrinks_square_and_gradient_is_diagnostic(self):
        mask = np.zeros((11, 11), dtype=np.uint8)
        mask[3:8, 3:8] = 255
        result = apply_morphology(mask, "erosion")
        expected = np.zeros_like(mask)
        expected[4:7, 4:7] = 255
        np.testing.assert_array_equal(result.mask, expected)
        control = apply_morphology(mask)
        np.testing.assert_array_equal(control.mask, mask)
        self.assertEqual(np.count_nonzero(control.gradient), 40)

    def test_opening_removes_speck_and_closing_fills_small_hole(self):
        mask = np.zeros((21, 21), dtype=np.uint8)
        mask[5:16, 5:16] = 255
        mask[10, 10] = 0
        mask[2, 2] = 255
        opened = apply_morphology(mask, "opening")
        self.assertEqual(opened.mask[2, 2], 0)
        self.assertEqual(opened.mask[10, 10], 0)
        closed = apply_morphology(mask, "closing")
        self.assertEqual(closed.mask[10, 10], 255)
        combined = apply_morphology(mask, "open_close")
        expected = np.zeros_like(mask)
        expected[5:16, 5:16] = 255
        np.testing.assert_array_equal(combined.mask, expected)
        self.assertEqual(combined.metadata["sequence"],
                         ["erosion", "dilation", "dilation", "erosion"])

    def test_empty_full_border_and_iterations(self):
        empty = np.zeros((9, 9), dtype=np.uint8)
        for operation in ("none", "erosion", "dilation", "opening", "closing", "open_close"):
            self.assertFalse(apply_morphology(empty, operation).mask.any())
        full = np.full((9, 9), 255, dtype=np.uint8)
        eroded = apply_morphology(full, "erosion", iterations=2)
        self.assertEqual(np.count_nonzero(eroded.mask), 25)
        self.assertEqual(eroded.mask[0, 0], 0)
        np.testing.assert_array_equal(apply_morphology(full, "dilation").mask, full)
        corner = empty.copy()
        corner[0, 0] = 255
        self.assertEqual(np.count_nonzero(apply_morphology(corner, "dilation").mask), 4)

    def test_identity_footprint_and_binary_contract(self):
        mask = np.eye(9, dtype=np.uint8)
        for operation in ("none", "erosion", "dilation", "opening", "closing", "open_close"):
            result = apply_morphology(mask, operation, kernel_size=1)
            np.testing.assert_array_equal(result.mask, mask * 255)
            self.assertEqual(result.mask.dtype, np.uint8)
            self.assertFalse(np.shares_memory(result.mask, mask))

    def test_invalid_inputs_fail_explicitly(self):
        mask = np.zeros((9, 9), dtype=np.uint8)
        for kwargs in ({"operation": "invented"}, {"kernel_size": 2}, {"kernel_size": 17},
                       {"kernel_size": True}, {"kernel_shape": "triangle"}, {"iterations": 0},
                       {"iterations": 6}, {"iterations": 1.5}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                apply_morphology(mask, **kwargs)
        for bad in (np.zeros((2, 2, 3)), np.zeros((0, 0)), np.array([[128]]),
                    np.array([[float("nan")]])):
            with self.assertRaises(ValueError):
                apply_morphology(bad)

    def test_matches_opencv_with_explicit_zero_border(self):
        try:
            import cv2
        except ImportError:
            self.skipTest("OpenCV unavailable; analytical cases still run.")
        rng = np.random.default_rng(42)
        mask = (rng.random((31, 29)) > .35).astype(np.uint8) * 255
        for shape in ("square", "cross", "disk"):
            for operation, code in (("erosion", cv2.MORPH_ERODE), ("dilation", cv2.MORPH_DILATE),
                                    ("opening", cv2.MORPH_OPEN), ("closing", cv2.MORPH_CLOSE)):
                for iterations in (1, 2):
                    with self.subTest(shape=shape, operation=operation, iterations=iterations):
                        actual = apply_morphology(mask, operation, kernel_size=5,
                                                  kernel_shape=shape, iterations=iterations)
                        expected = cv2.morphologyEx(mask, code, structuring_element(5, shape),
                                                   iterations=iterations, borderType=cv2.BORDER_CONSTANT,
                                                   borderValue=0)
                        np.testing.assert_array_equal(actual.mask, expected)


class MorphologyPipelineTests(unittest.TestCase):
    def fixture(self, folder):
        mask = np.zeros((64, 64), dtype=np.uint8)
        mask[16:48, 16:48] = 255
        mask[30, 30] = 0
        mask[5, 5] = 255
        pixels = np.full((64, 64, 3), 255, dtype=np.uint8)
        pixels[mask > 0] = (20, 40, 60)
        path = Path(folder) / "synthetic.png"
        Image.fromarray(pixels).save(path)
        return path, mask, replace(load_config(), image_size=(64, 64))

    def test_morphology_changes_mask_without_erasing_classifier_pixels(self):
        with tempfile.TemporaryDirectory() as folder:
            path, expected, config = self.fixture(folder)
            base = ProcessingPipelineOptions(filter_name="none", segmentation_name="otsu",
                                             segmentation_parameters={"invert": True}, morphology_name="none")
            control = run_processing_pipeline(path, config, base)
            np.testing.assert_array_equal(control.segmentation_result.mask, expected)
            self.assertIs(control.segmentation_result, control.raw_segmentation_result)
            processed = run_processing_pipeline(path, config, replace(base, morphology_name="open_close"))
            np.testing.assert_array_equal(processed.raw_segmentation_result.mask, expected)
            self.assertEqual(processed.segmentation_result.mask[30, 30], 255)
            self.assertEqual(processed.segmentation_result.mask[5, 5], 0)
            np.testing.assert_array_equal(processed.segmentation_result.image,
                                          apply_mask(processed.filter_result.image, processed.morphology_result.mask))
            np.testing.assert_array_equal(processed.recognition_image, processed.filter_result.image)
            self.assertEqual(processed.metadata["morphology"]["changed_pixels"], 2)

    def test_classifier_receives_rgb_and_mask_remains_diagnostic(self):
        from types import SimpleNamespace
        from ecoscan.services.analysis_service import analyze_waste_image
        from ecoscan.classification.baseline import BaselinePrediction
        with tempfile.TemporaryDirectory() as folder:
            path, _, config = self.fixture(folder)
            options = ProcessingPipelineOptions(
                filter_name="none", segmentation_name="otsu",
                segmentation_parameters={"invert": True}, morphology_name="open_close")
            prediction = BaselinePrediction(None, "metal", .1, {"metal": .1}, False, .6)
            with patch("ecoscan.services.analysis_service._predict", return_value=prediction) as predict, \
                 patch("ecoscan.services.analysis_service.apply_material_rules", return_value=(prediction, None)):
                result = analyze_waste_image(path, config, options=options,
                                             model_bundle=SimpleNamespace(model_type="test"))
            np.testing.assert_array_equal(predict.call_args.args[1], result.pipeline.recognition_image)
            self.assertFalse(np.all(predict.call_args.args[1][5, 5] == 255))
            self.assertEqual(result.pipeline.segmentation_result.mask[5, 5], 0)

    def test_lossless_exports_and_metadata_include_intermediate_stages(self):
        with tempfile.TemporaryDirectory() as folder:
            path, _, config = self.fixture(folder)
            result = run_processing_pipeline(path, config, ProcessingPipelineOptions(
                filter_name="none", segmentation_name="otsu",
                segmentation_parameters={"invert": True}, morphology_name="opening"))
            target = Path(folder) / "evidence"
            artifacts = save_pipeline_artifacts(result, target)
            self.assertEqual(artifacts[-1].name, "pipeline_report.json")
            with Image.open(target / "11_mask_after_morphology.png") as image:
                np.testing.assert_array_equal(np.asarray(image), result.morphology_result.mask)
            self.assertTrue((target / "morphology_01_erosion.png").exists())
            metadata = json.loads((target / "pipeline_report.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["morphology"]["kernel"], [[1, 1, 1]] * 3)
            self.assertEqual(metadata["morphology"]["sequence"], ["erosion", "dilation"])
            self.assertIn("aspect ratio preserved", metadata["preprocessing"]["resize"])


if __name__ == "__main__":
    unittest.main()
