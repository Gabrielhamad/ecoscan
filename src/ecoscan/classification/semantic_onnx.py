"""Compact experimental recognition. No PyTorch or pickle required in the app."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import shutil
from threading import Lock

import numpy as np
from ecoscan.classification.baseline import BaselinePrediction


def softmax(values):
    values = np.asarray(values, dtype=np.float64)
    shifted = np.exp(values - np.max(values))
    return shifted / shifted.sum()


def file_digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def resolve_encoder(folder, metadata):
    name = metadata.get("encoder_file", "encoder_int8.onnx")
    if name not in {"encoder_int8.onnx", "encoder.onnx"}:
        raise ValueError("Invalid encoder path")
    encoder = folder / name
    if encoder.exists() and file_digest(encoder) == metadata["encoder_sha256"]:
        return encoder
    parts = metadata.get("parts", [])
    if not 1 <= len(parts) <= 4:
        raise ValueError("Encoder missing or corrupt")
    for index, part in enumerate(parts):
        if part["name"] != f"encoder_{index:02d}.part" or file_digest(folder / part["name"]) != part["sha256"]:
            raise ValueError("Invalid encoder part")
    temporary = folder / "encoder.tmp"
    try:
        with temporary.open("wb") as output:
            for part in parts:
                with (folder / part["name"]).open("rb") as source:
                    shutil.copyfileobj(source, output)
        if file_digest(temporary) != metadata["encoder_sha256"]:
            raise ValueError("Invalid combined encoder")
        temporary.replace(encoder)
    finally:
        temporary.unlink(missing_ok=True)
    return encoder


class SemanticOnnxClassifier:
    def __init__(self, path, encoder_folder=None):
        import onnxruntime as ort
        path = Path(path)
        self.metadata = json.loads(path.read_text(encoding="utf-8"))
        if self.metadata["format"] not in {"clip-probe-int8-v1", "clip-probe-fp16-v1"}:
            raise ValueError("Unsupported semantic model")
        encoder = resolve_encoder(Path(encoder_folder) if encoder_folder else path.parent, self.metadata)
        if file_digest(path.parent / "head.npz") != self.metadata["head_sha256"]:
            raise ValueError("Semantic artifact integrity mismatch")
        with np.load(path.parent / "head.npz", allow_pickle=False) as data:
            self.arrays = {name: data[name].copy() for name in data.files}
        self.classes = self.metadata["classes"]
        options = ort.SessionOptions()
        options.log_severity_level = 3
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(encoder),
                                           sess_options=options, providers=["CPUExecutionProvider"])
        self.lock = Lock()

    def image_features(self, rgb):
        if rgb.shape != (224, 224, 3) or rgb.dtype != np.uint8:
            raise ValueError("Expected prepared RGB image")
        image = rgb.astype(np.float32) / 255.0
        image = (image - np.array([.48145466, .4578275, .40821073], dtype=np.float32)) / np.array(
            [.26862954, .26130258, .27577711], dtype=np.float32)
        with self.lock:
            feature = self.session.run(None, {"image": image.transpose(2, 0, 1)[None]})[0][0]
        return feature

    def predict_image(self, rgb):
        return self.predict_features(self.image_features(rgb))

    def predict_features(self, feature):
        a = self.arrays
        prior = softmax(a["logit_scale"] * feature @ a["prototypes"].T)
        probe = softmax(((feature - a["mean"]) / a["scale"]) @ a["coef"].T + a["intercept"])
        aligned = np.zeros(len(self.classes))
        for index, label in enumerate(self.metadata["head_classes"]):
            aligned[self.classes.index(label)] = probe[index]
        weight = self.metadata["prior_weight"]
        scores = weight * prior + (1 - weight) * aligned
        if not np.isfinite(scores).all() or not np.isclose(scores.sum(), 1):
            raise ValueError("Invalid semantic scores")
        label = self.classes[int(scores.argmax())]
        score, threshold = float(scores.max()), float(self.metadata["threshold"])
        accepted = label != "unknown" and score >= threshold
        return BaselinePrediction(label, label if accepted else None, score,
                                  dict(zip(self.classes, map(float, scores))), accepted, threshold)


_LOAD_LOCK = Lock()


@lru_cache(maxsize=1)
def _cached_model(path, encoder_folder=None):
    return SemanticOnnxClassifier(path, encoder_folder)


def load_semantic_model(path, encoder_folder=None):
    with _LOAD_LOCK:
        return _cached_model(path, encoder_folder)
