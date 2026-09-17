from __future__ import annotations

import unittest

import numpy as np
from PIL import Image

from ecoscan.app.pipeline import ProcessingPipelineOptions
from ecoscan.classification.baseline import BaselinePrediction
from ecoscan.config import PROJECT_ROOT
from ecoscan.live_camera.analyzer import LiveCameraAnalyzer
from ecoscan.live_camera.server import LIVE_CAMERA_HTML
from ecoscan.live_camera.tracking import CentroidTracker
from ecoscan.segmentation.elements import VisualElement


class LiveCameraTrackingTests(unittest.TestCase):
    def test_tracker_keeps_id_for_nearby_element(self) -> None:
        tracker = CentroidTracker(max_distance_ratio=0.25)
        first = VisualElement(
            label=1,
            bbox_xyxy=(20, 20, 80, 80),
            centroid_xy=(50.0, 50.0),
            area_pixels=3600,
            area_ratio=0.12,
            touches_border=False,
        )
        second = VisualElement(
            label=1,
            bbox_xyxy=(24, 22, 84, 82),
            centroid_xy=(54.0, 52.0),
            area_pixels=3600,
            area_ratio=0.12,
            touches_border=False,
        )

        first_tracks = tracker.update([first], frame_width=224, frame_height=224)
        second_tracks = tracker.update([second], frame_width=224, frame_height=224)

        self.assertEqual(first_tracks[0].track_id, second_tracks[0].track_id)
        self.assertEqual(second_tracks[0].age_frames, 2)


class LiveCameraHtmlTests(unittest.TestCase):
    def test_live_camera_prioritizes_rear_camera_on_mobile(self) -> None:
        self.assertIn('let facingMode = "environment";', LIVE_CAMERA_HTML)
        self.assertIn('videoConstraints.facingMode = { exact: mode };', LIVE_CAMERA_HTML)
        self.assertIn('videoConstraints.facingMode = { ideal: mode };', LIVE_CAMERA_HTML)
        self.assertIn("backCameraPattern", LIVE_CAMERA_HTML)
        self.assertIn("câmera ativa; traseira não confirmada", LIVE_CAMERA_HTML)
        self.assertIn("Iniciar traseira", LIVE_CAMERA_HTML)


class FakeBundle:
    model_type = "fake_live_model"


class LiveCameraAnalyzerTests(unittest.TestCase):
    def test_analyzer_returns_structured_error_for_empty_frame(self) -> None:
        live_analyzer = LiveCameraAnalyzer(
            _fake_config(),
            model_bundle=FakeBundle(),
            tracker=CentroidTracker(),
        )

        payload = live_analyzer.analyze_frame(b"")

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "CAM-001")
        self.assertIn("action", payload)

    def test_analyzer_returns_detection_payload(self) -> None:
        from ecoscan.live_camera import analyzer as analyzer_module

        original_predict = analyzer_module.analyze_waste_image
        image = Image.new("RGB", (96, 96), (40, 130, 90))
        image_bytes = _image_bytes(image)

        def fake_analyze_waste_image(image_path, config, *, options=None, model_bundle=None):
            pipeline = _fake_pipeline()
            prediction = BaselinePrediction(
                top_class_id="metal",
                class_id="metal",
                probability=0.91,
                probabilities={"metal": 0.91},
                accepted=True,
                threshold=0.45,
            )
            return type(
                "Result",
                (),
                {
                    "pipeline": pipeline,
                    "predicted_class": prediction.class_id,
                    "top_class": prediction.top_class_id,
                    "probability": prediction.probability,
                    "accepted": prediction.accepted,
                    "message": "Categoria identificada: Metal.",
                    "guidance": type(
                        "Guidance",
                        (),
                        {
                            "display_name": "Metal",
                            "environmental_category": "Reciclável",
                            "guidance": "Encaminhar para coleta seletiva.",
                            "educational_note": "Metais podem ser reciclados.",
                        },
                    )(),
                    "probabilities": prediction.probabilities,
                    "model_type": model_bundle.model_type,
                },
            )()

        try:
            analyzer_module.analyze_waste_image = fake_analyze_waste_image
            live_analyzer = LiveCameraAnalyzer(
                _fake_config(),
                model_bundle=FakeBundle(),
                tracker=CentroidTracker(),
            )
            payload = live_analyzer.analyze_frame(image_bytes)
        finally:
            analyzer_module.analyze_waste_image = original_predict

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["predicted_class"], "metal")
        self.assertEqual(payload["probabilities"]["metal"], 0.91)
        self.assertEqual(payload["disposal_target"]["destination_title"], "Lixeira amarela")
        self.assertEqual(payload["environmental_impact"]["risk_label"], "Desperdício de material reciclável")
        self.assertEqual(payload["detections"][0]["track_id"], 1)
        self.assertEqual(payload["detections"][0]["label"], "Metal")


def _image_bytes(image: Image.Image) -> bytes:
    import io

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def _fake_config():
    return type(
        "Config",
        (),
        {
            "project_root": PROJECT_ROOT,
            "image_size": (224, 224),
        },
    )()


def _fake_pipeline():
    element = VisualElement(
        label=1,
        bbox_xyxy=(10, 12, 110, 120),
        centroid_xy=(60.0, 66.0),
        area_pixels=10_800,
        area_ratio=0.215,
        touches_border=False,
    )
    analysis = type(
        "Analysis",
        (),
        {
            "image_width": 224,
            "image_height": 224,
            "warning": "segmentação isolou um elemento principal de forma plausível",
            "elements": (element,),
        },
    )()
    return type(
        "Pipeline",
        (),
        {
            "element_analysis": analysis,
            "metadata": {
                "filter": {"name": "auto"},
                "segmentation": {"name": "otsu"},
                "quality": {"before_filter": {}, "after_filter": {}},
                "capture_quality": {"status": "good", "score": 94, "title": "Captura adequada"},
            },
        },
    )()


if __name__ == "__main__":
    unittest.main()
