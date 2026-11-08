from __future__ import annotations

import unittest

from PIL import Image

from ecoscan.classification.prediction import ClassificationPrediction
from ecoscan.config import PROJECT_ROOT
from ecoscan.live_camera.analyzer import LiveCameraAnalyzer, _suggested_target_payload
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
        self.assertNotIn('id="scoreRing"', LIVE_CAMERA_HTML)
        self.assertNotIn('id="probabilities"', LIVE_CAMERA_HTML)
        self.assertNotIn('id="score"', LIVE_CAMERA_HTML)
        self.assertNotIn("renderProbabilities(", LIVE_CAMERA_HTML)
        self.assertIn("confirme para descartar", LIVE_CAMERA_HTML)
        self.assertIn('id="manualCorrection"', LIVE_CAMERA_HTML)
        self.assertNotIn("categoria confirmada", LIVE_CAMERA_HTML)


class FakeBundle:
    model_type = "fake_live_model"


class LiveCameraAnalyzerTests(unittest.TestCase):
    def test_suggested_color_is_not_a_confirmed_disposal_instruction(self) -> None:
        from ecoscan.disposal.targets import load_disposal_targets
        targets = load_disposal_targets(PROJECT_ROOT / "config" / "disposal_targets.json")
        result = _suggested_target_payload("metal", targets)
        self.assertEqual(result["destination_title"], "Lixeira amarela")
        self.assertNotIn("preparation_steps", result)
        self.assertNotIn("map_url", result)
        self.assertIsNone(_suggested_target_payload("unknown", targets))


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
        original_decide = analyzer_module.decision_for_result
        image = Image.new("RGB", (96, 96), (40, 130, 90))
        image_bytes = _image_bytes(image)

        def fake_analyze_waste_image(image_path, config, *, options=None, model_bundle=None):
            pipeline = _fake_pipeline()
            prediction = ClassificationPrediction(
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
                    "decision": _fake_decision(),
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
            analyzer_module.decision_for_result = lambda result, config: _fake_decision()
            live_analyzer = LiveCameraAnalyzer(
                _fake_config(),
                model_bundle=FakeBundle(),
                tracker=CentroidTracker(),
            )
            payload = live_analyzer.analyze_frame(image_bytes)
        finally:
            analyzer_module.analyze_waste_image = original_predict
            analyzer_module.decision_for_result = original_decide

        self.assertTrue(payload["ok"])
        self.assertIsNone(payload["predicted_class"])
        self.assertFalse(payload["accepted"])
        self.assertEqual(payload["decision"]["title"], "Melhor correspondência: METAL")
        self.assertNotIn("probabilities", payload)
        self.assertNotIn("probability", payload)
        self.assertNotIn("score", payload["detections"][0])
        self.assertEqual(payload["suggested_target"]["destination_title"], "Lixeira amarela")
        self.assertIsNone(payload["disposal_target"])
        self.assertIsNone(payload["environmental_impact"])
        self.assertEqual(payload["detections"][0]["track_id"], 1)
        self.assertEqual(payload["detections"][0]["label"], "Região visual")


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


def _fake_decision():
    from types import SimpleNamespace
    return SimpleNamespace(status="probable", tone="warn", title="Melhor correspondência: METAL",
                           message="Confirme para descartar.", primary_action="Confira o material no aplicativo.",
                           suggested_class="metal", requires_confirmation=True, can_correct=True)


if __name__ == "__main__":
    unittest.main()
