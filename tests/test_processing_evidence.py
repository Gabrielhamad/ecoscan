import io
import json
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from PIL import Image
from streamlit.testing.v1 import AppTest

from ecoscan.app.pipeline import ProcessingPipelineOptions, default_processing_options, run_processing_pipeline
from ecoscan.config import load_config
from ecoscan.classification.baseline import BaselinePrediction
from ecoscan.services.analysis_service import analyze_waste_image
from ecoscan.services.processing_evidence import (
    ProcessingEvidence, array_digest, evidence_manifest, processing_evidence, processing_evidence_zip,
)
from ecoscan.segmentation.methods import apply_mask


class AppliedProcessingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "private-upload.png"
        self.config = replace(load_config(), image_size=(64, 64))
        # Known salt-and-pepper defects within a contrasting object and background.
        pixels = np.full((64, 64, 3), 240, dtype=np.uint8)
        pixels[16:48, 16:48] = (30, 50, 70)
        pixels[30, 30] = 255
        pixels[4, 4] = 0
        self.pixels = pixels
        Image.fromarray(pixels).save(self.path)

    def test_default_executes_filter_segmentation_and_four_primitives(self):
        result = run_processing_pipeline(self.path, self.config)
        self.assertEqual(result.metadata["filter"]["decision"]["requested"], "auto")
        self.assertEqual(result.metadata["segmentation"]["decision"]["requested"], "auto")
        self.assertEqual(result.morphology_result.metadata["operation"], "open_close")
        self.assertEqual([name for name, _ in result.morphology_result.stages],
                         ["erosion", "dilation", "dilation", "erosion"])
        self.assertEqual(result.filter_result.image.shape, (64, 64, 3))
        self.assertEqual(result.raw_segmentation_result.mask.shape, (64, 64))
        stages = processing_evidence(result)
        self.assertEqual(len(stages), 8)
        self.assertTrue(all(stage.applied for stage in stages))
        self.assertIsNotNone(stages[1].changed_pixels)
        self.assertIsNone(stages[2].changed_pixels)  # RGB and binary mask differ in representation.
        for stage in stages[3:7]:
            self.assertGreater(stage.changed_pixels, 0)

    def test_actual_arrays_form_morphology_chain_and_classifier_input(self):
        prediction = BaselinePrediction(None, "metal", .1, {"metal": .1}, False, .6)
        with patch("ecoscan.services.analysis_service._predict", return_value=prediction) as predict, \
             patch("ecoscan.services.analysis_service.apply_material_rules", return_value=(prediction, None)):
            result = analyze_waste_image(self.path, self.config,
                                         model_bundle=SimpleNamespace(model_type="test"))
        pipeline = result.pipeline
        stages = processing_evidence(pipeline)
        self.assertIs(stages[1].before, pipeline.preprocessing.resized)
        self.assertIs(stages[1].after, pipeline.filter_result.image)
        self.assertIs(stages[2].after, pipeline.raw_segmentation_result.mask)
        for previous, current in zip(stages[2:6], stages[3:7]):
            self.assertIs(current.before, previous.after)
        self.assertIs(stages[-1].after, predict.call_args.args[1])
        np.testing.assert_array_equal(stages[-1].after,
                                      apply_mask(stages[-1].before, stages[-2].after))
        manifest = evidence_manifest(pipeline)
        self.assertEqual(manifest["classifier_input_sha256"], array_digest(predict.call_args.args[1]))
        self.assertEqual(stages[-1].parameters["mask_sha256"], array_digest(stages[-2].after))

    def test_controls_and_unchanged_execution_are_distinct(self):
        pixels = np.zeros((3, 3), dtype=np.uint8)
        executed = ProcessingEvidence("a", "Erosão", pixels, pixels.copy(), {}, True)
        control = replace(executed, applied=False)
        self.assertEqual(executed.changed_pixels, 0)
        self.assertIn("Executada", executed.status)
        self.assertIn("desativada", control.status)
        result = run_processing_pipeline(self.path, self.config, ProcessingPipelineOptions(
            filter_name="none", segmentation_name="none", morphology_name="none"))
        stages = processing_evidence(result)
        self.assertTrue(stages[0].applied)
        self.assertTrue(all(not stage.applied for stage in stages[1:]))
        self.assertEqual(stages[-1].changed_pixels, 0)

    def test_lossless_package_matches_arrays_without_private_paths(self):
        pipeline = run_processing_pipeline(self.path, self.config)
        with zipfile.ZipFile(io.BytesIO(processing_evidence_zip(pipeline))) as package:
            manifest_text = package.read("manifest.json").decode("utf-8")
            self.assertNotIn(str(self.path), manifest_text)
            self.assertNotIn("private-upload", manifest_text)
            self.assertNotIn("image_path", manifest_text)
            manifest = json.loads(manifest_text)
            for stage, record in zip(processing_evidence(pipeline), manifest["stages"]):
                for position in ("before", "after"):
                    with Image.open(io.BytesIO(package.read(stage.key + "_" + position + ".png"))) as image:
                        decoded = np.asarray(image)
                        np.testing.assert_array_equal(decoded, getattr(stage, position))
                        self.assertEqual(array_digest(decoded), record[position]["sha256"])
            with Image.open(io.BytesIO(package.read("antes_depois.png"))) as image:
                self.assertEqual(image.size, (960, 2472))

    def test_difference_uses_wide_arithmetic_no_uint8_wrap_or_amplification(self):
        before = np.array([[[255, 0, 90], [3, 3, 3]]], dtype=np.uint8)
        after = np.array([[[0, 255, 80], [3, 3, 3]]], dtype=np.uint8)
        stage = ProcessingEvidence("a", "test", before, after, {})
        np.testing.assert_array_equal(stage.difference, [[255, 0]])
        self.assertEqual(stage.changed_pixels, 1)

    def test_custom_configuration_and_control_remain_available(self):
        config = replace(self.config, filters={"default": "none"},
                         segmentation={"default": "none", "morphology": {"default": "none"}})
        result = run_processing_pipeline(self.path, config)
        self.assertEqual(default_processing_options(config).morphology_name, "none")
        np.testing.assert_array_equal(result.segmentation_result.image, self.pixels)

    def test_public_evidence_renders_all_pairs_and_download(self):
        # Real pipeline stored in this isolated test session, without any account or database.
        pipeline = run_processing_pipeline(self.path, self.config)
        app = AppTest.from_string("""
import streamlit as st
from ecoscan.ui.processing_lab import render_applied_processing
render_applied_processing(st, st.session_state.pipeline)
""", default_timeout=20)
        app.session_state["pipeline"] = pipeline
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.tabs), 8)
        self.assertEqual(len(app.get("download_button")), 1)
        self.assertTrue(any("Processamento aplicado" in item.value for item in app.subheader))
        for tab in app.tabs:
            self.assertGreaterEqual(len(tab.get("imgs")), 2)


if __name__ == "__main__":
    unittest.main()
