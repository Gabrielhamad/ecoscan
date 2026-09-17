from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from ecoscan.app.pipeline import ProcessingPipelineOptions, run_processing_pipeline
from ecoscan.config import load_config


class PipelineTests(unittest.TestCase):
    def test_pipeline_builds_all_processing_stages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "object.png"
            Image.new("RGB", (96, 80), (30, 30, 30)).save(path)
            config = load_config()

            result = run_processing_pipeline(
                path,
                config,
                ProcessingPipelineOptions(filter_name="auto", segmentation_name="auto"),
            )

            self.assertEqual(result.preprocessing.resized.shape, (224, 224, 3))
            self.assertEqual(result.filter_result.image.shape, (224, 224, 3))
            self.assertEqual(result.segmentation_result.mask.shape, (224, 224))
            self.assertEqual(result.element_overlay.shape, (224, 224, 3))
            self.assertEqual(result.detection_heatmap.shape, (224, 224, 3))
            self.assertEqual(result.model_input_preview.shape, (224, 224, 3))
            self.assertEqual(result.metadata["model_input_shape"], [1, 224, 224, 3])
            self.assertEqual(result.metadata["filter"]["decision"]["requested"], "auto")
            self.assertIn("selected_sequence", result.metadata["filter"]["decision"])
            self.assertIn("candidates", result.metadata["filter"]["decision"])
            self.assertEqual(result.metadata["segmentation"]["decision"]["requested"], "auto")
            self.assertEqual(result.metadata["segmentation"]["decision"]["selected"], result.segmentation_result.name)
            self.assertIn("quality", result.metadata)
            self.assertIn("elements", result.metadata)
            self.assertIn("visual_explanation", result.metadata)


if __name__ == "__main__":
    unittest.main()
