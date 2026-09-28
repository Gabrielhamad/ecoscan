import unittest
from dataclasses import replace

from streamlit.testing.v1 import AppTest
from ecoscan.app.pipeline import ProcessingPipelineOptions
from ecoscan.ui.streamlit_app import _input_signature
from tests.test_streamlit_camera_flow import FakeUploadedFile


class ProcessingLabTests(unittest.TestCase):
    def app(self):
        return AppTest.from_string("""
import streamlit as st
import numpy as np
from types import SimpleNamespace
from ecoscan.image_processing.preprocessing import prepare_model_input
from ecoscan.segmentation.morphology import apply_morphology
from ecoscan.ui.processing_lab import select_morphology_parameters, render_processing_lab
operation, parameters = select_morphology_parameters(st)
mask = np.zeros((32, 32), dtype=np.uint8)
mask[8:24, 8:24] = 255
mask[2, 2] = 255
image = np.repeat(mask[..., None], 3, axis=2)
pipeline = SimpleNamespace(
    preprocessing=prepare_model_input(image, (32,32)),
    filter_result=SimpleNamespace(image=image),
    raw_segmentation_result=SimpleNamespace(mask=mask),
    morphology_result=apply_morphology(mask, operation, **parameters))
render_processing_lab(st, pipeline)
""", default_timeout=15)

    def test_controls_and_before_after_render(self):
        app = self.app().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="morphology_operation").value, "open_close")
        self.assertEqual(app.metric[2].value, "1")
        app.selectbox(key="morphology_operation").select("none").run()
        self.assertEqual(app.metric[2].value, "0")
        app.selectbox(key="morphology_operation").select("opening").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[2].value, "1")
        self.assertTrue(app.dataframe)
        self.assertTrue(any("erosion" in m.value and "dilation" in m.value for m in app.markdown))
        app.selectbox(key="morphology_shape").select("cross").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 3)

    def test_empty_mask_warning_after_excessive_erosion(self):
        app = self.app().run()
        app.selectbox(key="morphology_operation").select("erosion").run()
        app.select_slider(key="morphology_size").set_value(15)
        app.slider(key="morphology_iterations").set_value(5).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("vazia" in w.value for w in app.warning))

    def test_each_morphology_parameter_invalidates_analysis_signature(self):
        image = FakeUploadedFile("same.png", b"same pixels")
        base = ProcessingPipelineOptions()
        baseline = _input_signature(image, "upload", base)
        for variant in (
            replace(base, morphology_name="dilation"),
            replace(base, morphology_parameters={"kernel_size": 5}),
            replace(base, morphology_parameters={"kernel_shape": "cross"}),
            replace(base, morphology_parameters={"iterations": 2}),
        ):
            self.assertNotEqual(baseline, _input_signature(image, "upload", variant))

    def test_public_app_exposes_controls_outside_hidden_sidebar(self):
        from unittest.mock import patch
        from ecoscan.services.accounts import UserProfile
        with patch("ecoscan.ui.streamlit_app.render_identity",
                   return_value=UserProfile("visitor_lab", "Visitante", "user")):
            app = AppTest.from_string(
                "from ecoscan.ui.streamlit_app import main\nmain()", default_timeout=30).run()
            self.assertFalse(app.exception)
            self.assertFalse(any(x.key == "morphology_operation" for x in app.sidebar.selectbox))
            self.assertEqual(app.selectbox(key="public_filter").value, "auto")
            self.assertEqual(app.selectbox(key="public_segmentation").value, "auto")
            self.assertEqual(app.selectbox(key="morphology_operation").value, "open_close")
            app.selectbox(key="morphology_operation").select("dilation").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.select_slider(key="morphology_size").value, 3)


if __name__ == "__main__":
    unittest.main()
