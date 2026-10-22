from types import SimpleNamespace
from threading import Lock
from unittest.mock import patch
import hashlib
import pytest

import numpy as np

from ecoscan.classification.baseline import BaselinePrediction
from ecoscan.classification.semantic_onnx import SemanticOnnxClassifier, softmax, resolve_encoder
from ecoscan.services.analysis_service import SemanticPreviewBundle, _predict
from ecoscan.services.recognition_safety import build_recognition_safety_decision


def test_semantic_preview_requires_confirmation_even_at_high_score():
    result = SimpleNamespace(model_type="semantic_onnx_preview", probability=.99,
                             accepted=True, guidance=object())
    decision = build_recognition_safety_decision(result)
    assert decision.status == "needs_confirmation"
    assert not decision.allow_disposal_guidance
    assert decision.encourage_feedback


def test_semantic_predict_dispatch():
    prediction = BaselinePrediction("metal", "metal", .9, {"metal": .9}, True, .8)
    classifier = SimpleNamespace(predict_image=lambda image: prediction)
    assert _predict(None, None, SemanticPreviewBundle(classifier, ["metal"])) == prediction


def test_compact_head_alignment_and_preparation():
    model = SemanticOnnxClassifier.__new__(SemanticOnnxClassifier)
    model.classes = ["glass", "metal", "unknown"]
    model.metadata = {"head_classes": ["metal", "glass"], "prior_weight": .5, "threshold": .8}
    model.lock = Lock()
    model.session = SimpleNamespace(run=lambda *args: [np.array([[1., 0.]])])
    model.arrays = {"logit_scale": 10., "prototypes": np.array([[0., 1.], [1., 0.], [-1., 0.]]),
                    "mean": np.zeros(2), "scale": np.ones(2),
                    "coef": np.array([[10., 0.], [-10., 0.]]), "intercept": np.zeros(2)}
    prediction = model.predict_image(np.zeros((224, 224, 3), dtype=np.uint8))
    assert prediction.top_class_id == "metal"
    assert prediction.accepted
    assert abs(sum(prediction.probabilities.values()) - 1) < 1e-6


def test_softmax_handles_large_logits():
    assert np.allclose(softmax([10000., 10000.]), [.5, .5])


def test_encoder_parts_are_verified_and_reassembled(tmp_path):
    data = b"encoder contents"
    (tmp_path / "encoder_00.part").write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    metadata = {"encoder_file": "encoder.onnx", "encoder_sha256": digest,
                "parts": [{"name": "encoder_00.part", "sha256": digest}]}
    path = resolve_encoder(tmp_path, metadata)
    assert path.read_bytes() == data
    path.write_bytes(b"corrupted cache")
    assert resolve_encoder(tmp_path, metadata).read_bytes() == data


def test_encoder_rejects_untrusted_part_paths(tmp_path):
    metadata = {"encoder_file": "encoder.onnx", "encoder_sha256": "invalid",
                "parts": [{"name": "../outside.part", "sha256": "invalid"}]}
    with pytest.raises(ValueError):
        resolve_encoder(tmp_path, metadata)
    assert not (tmp_path / "encoder.onnx").exists()
