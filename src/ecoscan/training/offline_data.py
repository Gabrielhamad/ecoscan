"""Private local inputs and content-addressed embeddings for offline experiments."""
from __future__ import annotations

import hashlib
from datetime import datetime
from importlib.metadata import version
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from typing import Any

import numpy as np
from PIL import Image

from ecoscan.app.pipeline import default_processing_options, run_processing_pipeline
from ecoscan.classification.semantic_onnx import SemanticOnnxClassifier, file_digest
from ecoscan.config import AppConfig
from ecoscan.image_processing.contracts import processing_contract
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.services.evaluation_manifest import audit_evaluation_manifest
from ecoscan.services.processing_evidence import array_digest

AUGMENTATIONS = {'none': 1.0, 'brightness-0.9': .9, 'brightness-1.1': 1.1}
LICENSES = {'private-consent', 'CC0-1.0', 'CC-BY-4.0', 'CC-BY-SA-4.0'}
TOKEN = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}\Z')


def digest_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    with path.open('x', encoding='utf-8') as file:
        json.dump(value, file, indent=2, sort_keys=True, allow_nan=False)
        file.write('\n')


def versions() -> dict[str, str]:
    return {name: version(name) for name in ('numpy', 'scikit-learn', 'onnxruntime', 'Pillow', 'opencv-python-headless')}


def code_digest(config: AppConfig) -> str:
    return digest_json({p.relative_to(config.project_root).as_posix(): file_digest(p)
                        for p in sorted((config.project_root / 'src').rglob('*.py'))})


def local_path(source: Path, row: dict[str, Any]) -> Path:
    # Paths/splits have already passed the shared evaluation manifest audit.
    root = source.resolve(strict=True)
    path = (root / row['path']).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Image escapes the local source root')
    return path


def audit_inputs(manifest_path: Path, audit_path: Path, policy_path: Path,
                 classes: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = json.loads(manifest_path.read_text())
    audit_evaluation_manifest(rows, allowed_classes=classes, require_groups=True)
    receipt = json.loads(audit_path.read_text())
    required = {'manifest_sha256': file_digest(manifest_path), 'policy_sha256': file_digest(policy_path),
                'audit_status': 'approved', 'scope': 'offline_training_and_evaluation'}
    if not isinstance(receipt, dict) or any(receipt.get(k) != v for k, v in required.items()):
        raise ValueError('External provenance audit must approve this exact manifest and policy')
    for field in ('reviewer_id', 'evidence_reference', 'reviewed_at'):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            raise ValueError('Missing external audit evidence reference')
    if any(not TOKEN.fullmatch(receipt[k]) for k in ('reviewer_id', 'evidence_reference')):
        raise ValueError('Use opaque audit references, not personal data')
    if datetime.fromisoformat(receipt['reviewed_at']).utcoffset() is None or receipt.get('development_overlap_reviewed') is not True:
        raise ValueError('Audit must date and review known development overlap')
    if receipt.get('approved_augmentations') != list(AUGMENTATIONS):
        raise ValueError('Audit must explicitly approve the documented augmentation set')
    rgb_seen, labels, primary = set(), {}, set()
    for row in rows:
        if (row.get('source_kind') != 'field_photo' or row.get('consent') is not True
                or not isinstance(row.get('license'), str) or row['license'] not in LICENSES):
            raise ValueError('Only consented, audited local field photos may enter an experiment')
        if row.get('independent_test', False) is not False:
            raise ValueError('Manifest metadata cannot certify independence')
        rgb = row.get('rgb_sha256')
        if not isinstance(rgb, str) or not re.fullmatch('[0-9a-f]{64}', rgb) or rgb in rgb_seen:
            raise ValueError('Missing or repeated decoded RGB hash')
        rgb_seen.add(rgb)
        for field in ('object_id', 'session_id'):
            if not TOKEN.fullmatch(row[field]):
                raise ValueError('Use opaque object/session identifiers')
        if row['object_id'] in labels and labels[row['object_id']] != row['class_id']:
            raise ValueError('Conflicting object labels')
        labels[row['object_id']] = row['class_id']
        key = row['split'], row['object_id']
        if row['split'] != 'train' and key in primary:
            raise ValueError('Choose one primary photo per validation/test object')
        primary.add(key)
    if {r['split'] for r in rows} != {'train', 'validation', 'test'}:
        raise ValueError('Separate train, validation and untouched test are required')
    return rows, receipt


def verify_images(source: Path, rows: list[dict[str, Any]], config: AppConfig) -> None:
    for row in rows:
        path = local_path(source, row)
        image = load_rgb_image(path, allowed_extensions=config.allowed_extensions, min_size=config.min_image_size)
        if (file_digest(path) != row['sha256'] or array_digest(image.array) != row['rgb_sha256']
                or image.info.format != {'.png': 'PNG', '.jpg': 'JPEG', '.jpeg': 'JPEG'}.get(Path(row['path']).suffix.lower())):
            raise ValueError('Local image changed or has an invalid format')


class EmbeddingCache:
    def __init__(self, folder: Path, model: SemanticOnnxClassifier, config: AppConfig):
        self.folder, self.model, self.config = folder, model, config
        self.identity = {'encoder': model.metadata['encoder_sha256'], 'processing': processing_contract(config),
                         'code': code_digest(config), 'versions': versions()}
        if model.metadata['processing'] != self.identity['processing']:
            raise ValueError('Encoder preparation is incompatible with the local profile')
        self.folder.mkdir(parents=True, exist_ok=True)

    def feature(self, source: Path, row: dict[str, Any], augmentation: str = 'none') -> np.ndarray:
        if augmentation not in AUGMENTATIONS or (augmentation != 'none' and row['split'] != 'train'):
            raise ValueError('Augmentations are restricted to training photos')
        verify_images(source, [row], self.config)  # Cache hits never bypass source integrity.
        key = digest_json({**self.identity, 'image': row['sha256'], 'augmentation': augmentation})
        array_path, meta_path = self.folder / (key + '.npy'), self.folder / (key + '.json')
        if array_path.exists() or meta_path.exists():
            saved = json.loads(meta_path.read_text()) if meta_path.exists() else {}
            if not array_path.exists() or saved.get('key') != key or saved.get('sha256') != file_digest(array_path):
                raise ValueError('Corrupt embedding cache; remove the affected local entry')
            feature = np.load(array_path, allow_pickle=False)
        else:
            path = local_path(source, row)
            if augmentation == 'none':
                pipeline = run_processing_pipeline(path, self.config, default_processing_options(self.config))
                feature = self.model.image_features(pipeline.recognition_image)
            else:
                original = load_rgb_image(path, allowed_extensions=self.config.allowed_extensions,
                                          min_size=self.config.min_image_size).array
                pixels = np.clip(np.rint(original.astype(float) * AUGMENTATIONS[augmentation]), 0, 255).astype(np.uint8)
                with TemporaryDirectory(prefix='ecoscan-offline-') as temporary:
                    augmented = Path(temporary) / 'augmentation.png'
                    Image.fromarray(pixels).save(augmented)
                    pipeline = run_processing_pipeline(augmented, self.config, default_processing_options(self.config))
                    feature = self.model.image_features(pipeline.recognition_image)
            feature = np.asarray(feature)  # Preserve the encoder's exact floating-point output.
            self._validate(feature)
            with array_path.open('xb') as file:
                np.save(file, feature, allow_pickle=False)
            write_json(meta_path, {'key': key, 'sha256': file_digest(array_path)})
        self._validate(feature)
        return feature.copy()

    def _validate(self, feature: np.ndarray) -> None:
        if (feature.shape != (self.model.arrays['prototypes'].shape[1],)
                or feature.dtype not in (np.dtype('float16'), np.dtype('float32'), np.dtype('float64'))
                or not np.isfinite(feature).all()):
            raise ValueError('Invalid cached embedding')
