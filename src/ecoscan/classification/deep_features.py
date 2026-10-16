"""Frozen MobileNetV2 representations and a supervised waste classification head."""
from __future__ import annotations

import hashlib
from pathlib import Path
from threading import Lock

import cv2
import numpy as np

from ecoscan.classification.baseline import BaselinePrediction
from ecoscan.image_processing.contracts import model_processing_compatible, processing_contract


BACKBONE_SHA256 = "c0c3f76d93fa3fd6580652a45618618a220fced18babf65774ed169de0432ad5"
BACKBONE_URL = "https://media.githubusercontent.com/media/onnx/models/main/validated/vision/classification/mobilenet/model/mobilenetv2-12.onnx"


def mobilenet_input(rgb: np.ndarray) -> np.ndarray:
    if rgb.shape != (224, 224, 3) or rgb.dtype != np.uint8:
        raise ValueError("MobileNet expects the EcoScan RGB uint8 preparation at 224x224.")
    scaled = rgb.astype(np.float32) / 255.0
    normalized = (scaled - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array(
        [0.229, 0.224, 0.225], dtype=np.float32
    )
    return np.ascontiguousarray(normalized.transpose(2, 0, 1)[None])


class MobileNetFeatures:
    """Use 1000 ImageNet logits as a frozen representation, not as waste labels."""

    def __init__(self, path: Path):
        if hashlib.sha256(path.read_bytes()).hexdigest() != BACKBONE_SHA256:
            raise ValueError("MobileNet weights do not match the verified training backbone.")
        self.net = cv2.dnn.readNetFromONNX(str(path))
        self.lock = Lock()

    def extract(self, rgb: np.ndarray) -> np.ndarray:
        blob = mobilenet_input(rgb)
        with self.lock:
            self.net.setInput(blob)
            feature = self.net.forward().reshape(-1).astype(np.float32)
        if feature.shape != (1000,) or not np.isfinite(feature).all():
            raise ValueError("Invalid MobileNet representation.")
        return feature


class DeepFeatureClassifier:
    def __init__(self, head, backbone: MobileNetFeatures, threshold: float):
        if not 0 < threshold <= 1:
            raise ValueError("Invalid confidence threshold.")
        self.head = head
        self.backbone = backbone
        self.threshold = threshold

    @classmethod
    def load(cls, directory: Path, config):
        """Load only a trusted local candidate matching the current RGB contract."""
        import joblib

        path = directory / "candidate.joblib"
        contract = processing_contract(config)
        if not model_processing_compatible(path, contract):
            raise ValueError("Candidate is not compatible with the current image preparation.")
        payload = joblib.load(path)
        if (payload.get("model_type") != "mobilenetv2_logits_logistic"
                or payload.get("processing") != contract
                or payload.get("backbone_sha256") != BACKBONE_SHA256
                or sorted(payload.get("classes", [])) != sorted(config.classes)
                or list(payload["head"].classes_) != payload["classes"]):
            raise ValueError("Candidate metadata or class labels are incompatible.")
        return cls(payload["head"], MobileNetFeatures(directory / "mobilenetv2-12.onnx"), payload["threshold"])

    def predict_image(self, image: np.ndarray) -> BaselinePrediction:
        scores = np.asarray(self.head.predict_proba(self.backbone.extract(image)[None])[0])
        if not np.isfinite(scores).all() or (scores < 0).any() or not np.isclose(scores.sum(), 1):
            raise ValueError("Invalid classifier probabilities.")
        classes = [str(label) for label in self.head.classes_]
        if len(classes) != len(scores):
            raise ValueError("Class labels do not match classifier outputs.")
        index = int(scores.argmax())
        confidence = float(scores[index])
        accepted = confidence >= self.threshold
        return BaselinePrediction(
            top_class_id=classes[index], class_id=classes[index] if accepted else None,
            probability=confidence, probabilities=dict(zip(classes, map(float, scores), strict=True)),
            accepted=accepted, threshold=self.threshold,
        )
