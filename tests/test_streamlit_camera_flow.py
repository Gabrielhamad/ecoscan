from __future__ import annotations

import unittest

from ecoscan.app.pipeline import ProcessingPipelineOptions
from ecoscan.ui.streamlit_app import _input_signature, _probability_bar


class FakeUploadedFile:
    def __init__(self, name: str, data: bytes) -> None:
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


class StreamlitCameraFlowTest(unittest.TestCase):
    def test_input_signature_changes_with_source_and_processing_options(self) -> None:
        uploaded_file = FakeUploadedFile("capture.jpg", b"same-image-bytes")
        default_options = ProcessingPipelineOptions(filter_name="auto", segmentation_name="otsu")
        tuned_options = ProcessingPipelineOptions(
            filter_name="gaussian",
            filter_parameters={"kernel_size": 7, "sigma": 1.5},
            segmentation_name="otsu",
        )

        default_camera = _input_signature(uploaded_file, "camera", default_options)
        repeated_camera = _input_signature(uploaded_file, "camera", default_options)
        tuned_camera = _input_signature(uploaded_file, "camera", tuned_options)
        default_upload = _input_signature(uploaded_file, "upload", default_options)

        self.assertEqual(default_camera, repeated_camera)
        self.assertNotEqual(default_camera, tuned_camera)
        self.assertNotEqual(default_camera, default_upload)

    def test_probability_bar_renders_bounded_width(self) -> None:
        html = _probability_bar(
            "metal",
            1.25,
            guidance_by_class={},
            predicted_class="metal",
            accepted=True,
        )

        self.assertIn("width: 100.0%", html)
        self.assertIn("metal", html)


if __name__ == "__main__":
    unittest.main()
