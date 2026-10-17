"""Optional PyTorch inference for isolated, validated fine-tuning bundles."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from ecoscan.classification.baseline import BaselinePrediction
from ecoscan.classification.deep_features import mobilenet_input
from ecoscan.image_processing.contracts import processing_contract


class FineTunedClassifier:
    def __init__(self, model, classes, threshold, temperature=1):
        if not 0 < threshold <= 1 or not 0 < temperature <= 10 or not classes or len(set(classes)) != len(classes):
            raise ValueError('Invalid neural classifier policy.')
        self.model = model.eval()
        self.classes = list(classes)
        self.threshold = threshold
        self.temperature = temperature

    @classmethod
    def load(cls, directory: Path, config):
        import torch
        from torchvision.models import mobilenet_v2

        metadata = json.loads((directory / 'fine_tuned.json').read_text(encoding='utf-8'))
        path = directory / 'fine_tuned.pth'
        if (metadata['architecture'] != 'torchvision_mobilenet_v2'
                or metadata['processing'] != processing_contract(config)
                or sorted(metadata['classes']) != sorted(config.classes)
                or not 0 < metadata['threshold'] <= 1
                or not 0 < metadata['temperature'] <= 10
                or hashlib.sha256(path.read_bytes()).hexdigest() != metadata['sha256']):
            raise ValueError('Incompatible fine-tuning bundle.')
        model = mobilenet_v2(weights=None, num_classes=len(metadata['classes']))
        model.load_state_dict(torch.load(path, map_location='cpu', weights_only=True))
        return cls(model, metadata['classes'], metadata['threshold'], metadata['temperature'])

    def predict_image(self, image: np.ndarray):
        import torch

        with torch.inference_mode():
            scores = torch.softmax(self.model(torch.from_numpy(mobilenet_input(image))) / self.temperature, dim=1)[0].numpy()
        if not np.isfinite(scores).all() or len(scores) != len(self.classes):
            raise ValueError('Invalid neural classifier output.')
        index = int(scores.argmax())
        score = float(scores[index])
        accepted = score >= self.threshold
        return BaselinePrediction(
            top_class_id=self.classes[index], class_id=self.classes[index] if accepted else None,
            probability=score, probabilities=dict(zip(self.classes, map(float, scores), strict=True)),
            accepted=accepted, threshold=self.threshold)
