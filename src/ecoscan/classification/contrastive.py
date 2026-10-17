"""Optional image/text waste classifier; relative scores require validation."""
from __future__ import annotations

from pathlib import Path
from threading import Lock
import hashlib
import json

import numpy as np
from PIL import Image
from ecoscan.classification.baseline import BaselinePrediction
from ecoscan.image_processing.contracts import processing_contract


PROMPTS = {
    'plastic': ['plastic bottles for recycling', 'a crushed plastic bottle', 'an empty PET water bottle',
                'a plastic food container', 'a plastic bag', 'plastic packaging'],
    'metal': ['an aluminum soda can', 'an aluminum energy drink can', 'a crushed metal beverage can',
              'an empty steel food tin', 'an aluminum foil tray', 'scrap metal'],
    'glass': ['glass bottles for recycling', 'an empty glass jar', 'broken glass shards',
              'a glass beverage bottle', 'a drinking glass', 'glass packaging'],
    'paper_cardboard': ['a cardboard box', 'flattened cardboard packaging', 'a sheet of paper',
                        'crumpled paper', 'paper packaging', 'newspaper'],
    'battery': ['AA batteries', 'AAA batteries', 'used household battery cells',
                'small cylindrical batteries', 'a pile of spent batteries', 'rechargeable battery cells'],
    'electronic': ['a broken mobile phone', 'a computer keyboard', 'a discarded computer mouse',
                   'electronic cables and chargers', 'a broken computer monitor', 'an electronic circuit board'],
    'unknown': ['food scraps', 'a person', 'a screenshot of computer code', 'a logo or infographic',
                'a landscape without waste', 'clothes and textiles'],
}

MODEL_NAME = 'ViT-B-32-quickgelu'
PRETRAINED = 'openai'


def accepted_scores(scores, threshold, classes):
    scores = np.asarray(scores)
    if (scores.ndim != 2 or scores.shape[1] != len(classes) or not len(classes)
            or not np.isfinite(scores).all() or (scores < 0).any()
            or not np.allclose(scores.sum(axis=1), 1) or not 0 < threshold <= 1):
        raise ValueError('Invalid relative scores or acceptance threshold.')
    predictions = np.asarray(classes)[scores.argmax(axis=1)]
    return (scores.max(axis=1) >= threshold) & (predictions != 'unknown')


def aligned_probe_scores(head, features, classes):
    probabilities = head.predict_proba(features)
    aligned = np.zeros((len(features), len(classes)))
    for index, label in enumerate(head.classes_):
        aligned[:, classes.index(str(label))] = probabilities[:, index]
    return aligned


class ContrastiveClassifier:
    def __init__(self, cache_dir: Path):
        import open_clip
        import torch

        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            MODEL_NAME, pretrained=PRETRAINED, cache_dir=str(cache_dir), device='cpu')
        self.model.eval()
        self.classes = sorted(PROMPTS)
        self.source = open_clip.get_pretrained_cfg(MODEL_NAME, PRETRAINED)
        self.lock = Lock()
        tokenizer = open_clip.get_tokenizer(MODEL_NAME)
        prototypes = []
        with torch.inference_mode():
            for label in self.classes:
                tokens = tokenizer([f'A photo of {description}.' for description in PROMPTS[label]])
                features = self.model.encode_text(tokens, normalize=True).mean(dim=0)
                prototypes.append(features / features.norm())
        self.prototypes = torch.stack(prototypes)

    def image_features(self, rgb):
        import torch

        if rgb.shape != (224, 224, 3) or rgb.dtype != np.uint8:
            raise ValueError('Contrastive inference requires prepared RGB uint8 224x224.')
        # Image is already square and prepared; native transform adds tensor/CLIP normalization.
        tensor = self.preprocess(Image.fromarray(rgb)).unsqueeze(0)
        with self.lock, torch.inference_mode():
            feature = self.model.encode_image(tensor, normalize=True)
            return feature[0].numpy()

    def scores_from_features(self, feature):
        import torch

        with torch.inference_mode():
            tensor = torch.from_numpy(np.asarray(feature, dtype=np.float32)).reshape(1, -1)
            logits = self.model.logit_scale.exp() * tensor @ self.prototypes.T
            return logits.softmax(dim=-1)[0].numpy()

    def relative_scores(self, rgb):
        return self.scores_from_features(self.image_features(rgb))


class ContrastiveProbeClassifier:
    """Trusted local bundle; optional dependency and weights are loaded explicitly."""

    def __init__(self, encoder, payload):
        if (payload['method'] not in {'zero_shot', 'supervised_mixture'}
                or payload['classes'] != encoder.classes
                or not 0 <= payload['prior_weight'] <= 1 or not 0 < payload['threshold'] <= 1
                or (payload['method'] == 'zero_shot' and payload['head'] is not None)
                or (payload['head'] is None and (payload['method'] != 'zero_shot' or payload['prior_weight'] != 1))):
            raise ValueError('Invalid contrastive bundle policy.')
        self.encoder = encoder
        self.payload = payload

    @classmethod
    def load(cls, directory, config, cache_dir):
        import joblib

        model_path = directory / 'contrastive_probe.joblib'
        summary = json.loads((directory / 'summary.json').read_text(encoding='utf-8'))
        if hashlib.sha256(model_path.read_bytes()).hexdigest() != summary['model_sha256']:
            raise ValueError('Contrastive model integrity check failed.')
        payload = joblib.load(model_path)
        if (payload['processing'] != processing_contract(config)
                or payload['model_name'] != MODEL_NAME or payload['pretrained'] != PRETRAINED
                or payload['prompts'] != PROMPTS or payload['classes'] != sorted(PROMPTS)
                or set(config.classes) != set(PROMPTS) - {'unknown'}
                or (payload['head'] is not None and (set(payload['head'].classes_) != set(config.classes)
                                                      or payload['head'].n_features_in_ != 512))):
            raise ValueError('Contrastive bundle is incompatible with classes or image preparation.')
        return cls(ContrastiveClassifier(cache_dir), payload)

    def predict_image(self, rgb):
        feature = self.encoder.image_features(rgb)
        prior = self.encoder.scores_from_features(feature)
        scores = prior
        if self.payload['head'] is not None:
            weight = self.payload['prior_weight']
            probe = aligned_probe_scores(self.payload['head'], feature[None], self.encoder.classes)[0]
            scores = weight * prior + (1 - weight) * probe
        accepted = bool(accepted_scores(scores[None], self.payload['threshold'], self.encoder.classes)[0])
        label = self.encoder.classes[int(scores.argmax())]
        return BaselinePrediction(top_class_id=label, class_id=label if accepted else None,
                                  probability=float(scores.max()), accepted=accepted,
                                  probabilities=dict(zip(self.encoder.classes, map(float, scores))),
                                  threshold=self.payload['threshold'])
