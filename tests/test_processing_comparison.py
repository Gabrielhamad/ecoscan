import unittest
from types import SimpleNamespace
import numpy as np
from streamlit.testing.v1 import AppTest
from ecoscan.ui.processing_comparison import comparison_metrics


class ProcessingComparisonTests(unittest.TestCase):
    def pipeline(self, before, after):
        return SimpleNamespace(preprocessing=SimpleNamespace(resized=before),
                               filter_result=SimpleNamespace(image=after))

    def test_unchanged_control(self):
        image = np.full((8, 8, 3), 120, dtype=np.uint8)
        self.assertEqual(comparison_metrics(self.pipeline(image, image)),
                         {'mean_absolute_change': 0.0, 'changed_pixel_percent': 0.0})

    def test_change_does_not_underflow_uint8(self):
        before = np.full((8, 8, 3), 255, dtype=np.uint8)
        after = np.zeros_like(before)
        result = comparison_metrics(self.pipeline(before, after))
        self.assertEqual(result['mean_absolute_change'], 255.0)
        self.assertEqual(result['changed_pixel_percent'], 100.0)
        self.assertTrue(np.all(before == 255))

    def test_different_sizes_are_rejected(self):
        with self.assertRaises(ValueError):
            comparison_metrics(self.pipeline(np.zeros((8, 8, 3)), np.zeros((4, 4, 3))))

    def test_view_renders_real_pipeline_without_recognition(self):
        app = AppTest.from_string('''
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image
import streamlit as st
from ecoscan.config import load_config
from ecoscan.app.pipeline import run_processing_pipeline, ProcessingPipelineOptions
from ecoscan.ui.processing_comparison import render_processing_comparison
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "sample.png"
    pixels = np.full((80, 80, 3), 230, dtype=np.uint8)
    pixels[20:60, 25:55] = [30, 130, 60]
    Image.fromarray(pixels).save(path)
    result = run_processing_pipeline(path, load_config(),
        ProcessingPipelineOptions(filter_name="gaussian", segmentation_name="otsu"))
    render_processing_comparison(st, result)
''').run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.subheader[0].value, 'Antes do reconhecimento')
        self.assertEqual(len(app.dataframe), 1)
