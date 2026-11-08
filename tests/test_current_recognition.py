import hashlib
from pathlib import Path
from threading import Lock
from types import SimpleNamespace

import numpy as np
import pytest

from ecoscan.classification.prediction import ClassificationPrediction
from ecoscan.classification.runtime import RecognitionModel
from ecoscan.classification.semantic_onnx import (
    SemanticOnnxClassifier,
    resolve_encoder,
    softmax,
)
from ecoscan.services.analysis_service import _predict
from ecoscan.services.recognition_safety import build_recognition_safety_decision


def test_current_recognizer_requires_confirmation_even_at_high_score():
    result = SimpleNamespace(
        model_type="semantic_onnx_assisted",
        top_class="metal",
        probabilities={"metal": .99, "glass": .01, "plastic": 0., "paper_cardboard": 0., "battery": 0., "electronic": 0., "unknown": 0.},
        probability=0.99,
        accepted=True,
        guidance=object(),
    )
    decision = build_recognition_safety_decision(result)
    assert decision.status == "probable"
    assert not decision.allow_disposal_guidance
    assert decision.encourage_feedback


def test_current_prediction_dispatch():
    prediction = ClassificationPrediction(
        "metal", "metal", 0.9, {"metal": 0.9}, True, 0.8
    )
    classifier = SimpleNamespace(predict_image=lambda image: prediction)
    bundle = RecognitionModel(classifier, ("metal",), Path("semantic.json"))
    assert _predict(None, bundle) == prediction


def test_compact_head_alignment_and_preparation():
    model = SemanticOnnxClassifier.__new__(SemanticOnnxClassifier)
    model.classes = ["glass", "metal", "unknown"]
    model.metadata = {
        "head_classes": ["metal", "glass"],
        "prior_weight": 0.5,
        "threshold": 0.8,
    }
    model.lock = Lock()
    model.session = SimpleNamespace(run=lambda *args: [np.array([[1.0, 0.0]])])
    model.arrays = {
        "logit_scale": 10.0,
        "prototypes": np.array([[0.0, 1.0], [1.0, 0.0], [-1.0, 0.0]]),
        "mean": np.zeros(2),
        "scale": np.ones(2),
        "coef": np.array([[10.0, 0.0], [-10.0, 0.0]]),
        "intercept": np.zeros(2),
    }
    prediction = model.predict_image(np.zeros((224, 224, 3), dtype=np.uint8))
    assert prediction.top_class_id == "metal"
    assert prediction.accepted
    assert abs(sum(prediction.probabilities.values()) - 1) < 1e-6


def test_softmax_handles_large_logits():
    assert np.allclose(softmax([10000.0, 10000.0]), [0.5, 0.5])


def test_encoder_parts_are_verified_and_reassembled(tmp_path):
    data = b"encoder contents"
    (tmp_path / "encoder_00.part").write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    metadata = {
        "encoder_file": "encoder.onnx",
        "encoder_sha256": digest,
        "parts": [{"name": "encoder_00.part", "sha256": digest}],
    }
    path = resolve_encoder(tmp_path, metadata)
    assert path.read_bytes() == data
    path.write_bytes(b"corrupted cache")
    assert resolve_encoder(tmp_path, metadata).read_bytes() == data


def test_encoder_rejects_untrusted_part_paths(tmp_path):
    metadata = {
        "encoder_file": "encoder.onnx",
        "encoder_sha256": "invalid",
        "parts": [{"name": "../outside.part", "sha256": "invalid"}],
    }
    with pytest.raises(ValueError):
        resolve_encoder(tmp_path, metadata)
    assert not (tmp_path / "encoder.onnx").exists()
