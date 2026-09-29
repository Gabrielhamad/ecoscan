import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from ecoscan.app.pipeline import ProcessingPipelineOptions, run_processing_pipeline
from ecoscan.config import load_config
from ecoscan.image_processing.adaptive_filters import apply_adaptive_filter_pipeline
from ecoscan.image_processing.contracts import model_processing_compatible, processing_contract, write_model_contract
from ecoscan.image_processing.preprocessing import letterbox_image, prepare_working_image
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.services.dataset_preparation import prepare_dataset_images
from ecoscan.segmentation.adaptive import CandidateScore, segment_image_adaptive


def reference_scene():
    image = np.full((160, 160, 3), (190, 200, 215), dtype=np.uint8)
    image[30:130, 45:115] = (135, 55, 40)
    image[30:36, 45:115] = (145, 150, 155)
    image[124:130, 45:115] = (145, 150, 155)
    return image


class PreservedProcessingTests(unittest.TestCase):
    def test_transparency_is_composited_instead_of_revealing_hidden_pixels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "transparent.png"
            rgba = np.full((64, 64, 4), (0, 0, 0, 0), dtype=np.uint8)
            rgba[20:40, 20:40] = (255, 0, 0, 255)
            Image.fromarray(rgba).save(path)
            loaded = load_rgb_image(path, allowed_extensions={".png"}, min_size=(48, 48))
            np.testing.assert_array_equal(loaded.array[0, 0], [255, 255, 255])
            np.testing.assert_array_equal(loaded.array[30, 30], [255, 0, 0])

    def test_preparation_refuses_overlapping_directories_even_with_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for output in (root, root / "inside", root.parent):
                with self.subTest(output=output), self.assertRaisesRegex(ValueError, "overlap"):
                    prepare_dataset_images(load_config(), source_dir=root, output_dir=output, overwrite=True)

    def test_preparation_refuses_to_mix_unversioned_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "prepared"
            output.mkdir()
            original = output / "old.png"
            Image.fromarray(reference_scene()).save(original)
            with self.assertRaisesRegex(ValueError, "contract"):
                prepare_dataset_images(load_config(), source_dir=root / "raw", output_dir=output)
            self.assertTrue(original.is_file())

    def test_clean_scene_and_regular_texture_are_unchanged(self):
        texture = np.zeros((96, 96, 3), dtype=np.uint8)
        texture[:, ::2] = 255
        for source in [reference_scene(), texture]:
            with self.subTest(shape=source.shape):
                result = apply_adaptive_filter_pipeline(source, load_config().filters)
                np.testing.assert_array_equal(source, result.filter_result.image)

    def test_impulse_correction_improves_known_reference(self):
        source = reference_scene()
        noisy = source.copy()
        rng = np.random.default_rng(42)
        mask = rng.random(source.shape[:2]) < 0.015
        noisy[mask] = 255
        result = apply_adaptive_filter_pipeline(noisy, load_config().filters)
        before_error = np.mean((noisy.astype(float) - source) ** 2)
        after_error = np.mean((result.filter_result.image.astype(float) - source) ** 2)
        self.assertLess(after_error, before_error * 0.5)
        self.assertEqual(result.decision["selected"], "median")

    def test_gaussian_noise_correction_improves_known_reference(self):
        source = reference_scene()
        noisy = np.clip(source.astype(float) + np.random.default_rng(42).normal(0, 9, source.shape), 0, 255).astype(np.uint8)
        result = apply_adaptive_filter_pipeline(noisy, load_config().filters)
        before_error = np.mean((noisy.astype(float) - source) ** 2)
        after_error = np.mean((result.filter_result.image.astype(float) - source) ** 2)
        self.assertLess(after_error, before_error * 0.8)

    def test_letterbox_preserves_complete_portrait_and_geometry(self):
        source = np.full((400, 200, 3), (25, 60, 150), dtype=np.uint8)
        working = prepare_working_image(source, 300)
        self.assertEqual(working.resized.shape, (300, 150, 3))
        result, metadata = letterbox_image(working.resized, (224, 224))
        self.assertEqual(metadata["content_box_xywh"], [56, 0, 112, 224])
        np.testing.assert_array_equal(result[:, 56:168], np.broadcast_to([25, 60, 150], (224, 112, 3)))

    def test_hsv_cannot_remove_silver_cap_from_classifier_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = reference_scene()
            path = Path(tmp) / "can.png"
            Image.fromarray(source).save(path)
            config = replace(load_config(), image_size=(160, 160))
            result = run_processing_pipeline(path, config, ProcessingPipelineOptions(
                filter_name="none", segmentation_name="hsv_color", morphology_name="none"))
            self.assertEqual(result.segmentation_result.mask[32, 70], 0)
            np.testing.assert_array_equal(result.recognition_image, source)

    def test_missing_foreground_preserves_photo_without_fake_detection(self):
        result = segment_image_adaptive(np.full((80, 80, 3), 120, dtype=np.uint8))
        self.assertEqual(result.decision["status"], "unresolved")
        self.assertEqual(result.segmentation.name, "none")

    def test_valid_mask_is_not_discarded_when_invalid_candidate_scores_higher(self):
        invalid = CandidateScore("otsu", .95, .99, .01, 1, .9, "test")
        valid = CandidateScore("grabcut", .7, .4, .01, 1, .4, "test")
        with patch("ecoscan.segmentation.adaptive._score_candidate", side_effect=[invalid, valid]):
            result = segment_image_adaptive(reference_scene())
        self.assertEqual(result.segmentation.name, "grabcut")
        self.assertEqual(result.decision["status"], "candidate")

    def test_edge_experiment_keeps_rgb_and_evidence_tracks_real_input(self):
        from ecoscan.services.processing_evidence import processing_evidence
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "can.png"
            source = reference_scene()
            Image.fromarray(source).save(path)
            config = replace(load_config(), image_size=(160, 160))
            result = run_processing_pipeline(path, config, ProcessingPipelineOptions(
                filter_name="canny", segmentation_name="none", morphology_name="none"))
            np.testing.assert_array_equal(result.recognition_image, source)
            self.assertIs(processing_evidence(result)[-1].before, result.preprocessing.resized)

    def test_model_contract_detects_changed_filters_and_changed_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.joblib"
            path.write_bytes(b"test model")
            config = load_config()
            contract = processing_contract(config)
            self.assertFalse(model_processing_compatible(path, contract))
            write_model_contract(path, contract)
            self.assertTrue(model_processing_compatible(path, contract))
            changed = replace(config, filters=dict(config.filters) | {"default": "median"})
            self.assertFalse(model_processing_compatible(path, processing_contract(changed)))
            path.write_bytes(b"different model")
            self.assertFalse(model_processing_compatible(path, contract))

    def test_stale_model_predictions_remain_unconfirmed(self):
        from types import SimpleNamespace
        from ecoscan.classification.baseline import BaselinePrediction
        from ecoscan.services.analysis_service import analyze_waste_image
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "can.png"
            Image.fromarray(reference_scene()).save(path)
            predicted = BaselinePrediction("metal", "metal", .99, {"metal": .99}, True, .6)
            with patch("ecoscan.services.analysis_service._predict", return_value=predicted), \
                 patch("ecoscan.services.analysis_service.apply_material_rules", return_value=(predicted, None)):
                result = analyze_waste_image(path, load_config(),
                                             model_bundle=SimpleNamespace(model_type="test"))
            self.assertFalse(result.processing_compatible)
            self.assertFalse(result.accepted)
            self.assertEqual(result.top_class, "metal")
            self.assertIsNone(result.guidance)


if __name__ == "__main__":
    unittest.main()
