"""Validate the shipped ONNX contract/integrity and run one technical CPU probe."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ecoscan.classification.semantic_onnx import SemanticOnnxClassifier, file_digest
from ecoscan.config import load_config
from ecoscan.image_processing.contracts import processing_contract


def check_metadata(folder: Path, expected_processing: dict, classes: tuple[str, ...]) -> dict:
    metadata = json.loads((folder / 'semantic.json').read_text())
    if metadata['processing'] != expected_processing:
        raise ValueError('Model processing contract is incompatible with the configured defaults')
    if set(metadata['classes']) != set(classes) | {'unknown'}:
        raise ValueError('Model class scope mismatch')
    if set(metadata['head_classes']) != set(classes):
        raise ValueError('Head class scope mismatch')
    if file_digest(folder / 'head.npz') != metadata['head_sha256']:
        raise ValueError('Head checksum mismatch')
    parts = metadata['parts']
    if not 1 <= len(parts) <= 4:
        raise ValueError('Invalid encoder part count')
    for index, part in enumerate(parts):
        if part['name'] != f'encoder_{index:02d}.part' or not re.fullmatch('[a-f0-9]{64}', part['sha256']):
            raise ValueError('Invalid encoder part declaration')
        path = folder / part['name']
        if path.is_symlink() or file_digest(path) != part['sha256']:
            raise ValueError('Encoder part checksum mismatch')
    return metadata


def check_model(folder: Path) -> dict:
    import numpy as np
    config = load_config()
    metadata = check_metadata(folder, processing_contract(config), config.classes)
    # Reuse the inference implementation; assemble only in a temporary directory.
    with tempfile.TemporaryDirectory(prefix='ecoscan-model-ci-') as temporary:
        encoder_folder = Path(temporary)
        for part in metadata['parts']:
            shutil.copyfile(folder / part['name'], encoder_folder / part['name'])
        classifier = SemanticOnnxClassifier(folder / 'semantic.json', encoder_folder=encoder_folder)
        prediction = classifier.predict_image(np.full((224, 224, 3), 127, dtype=np.uint8))
        if set(prediction.probabilities) != set(metadata['classes']):
            raise ValueError('Inference output scope mismatch')
    return {'metadata_sha256': file_digest(folder / 'semantic.json'),
            'head_sha256': metadata['head_sha256'], 'encoder_sha256': metadata['encoder_sha256'],
            'processing_sha256': metadata['processing']['sha256'],
            'runtime': 'CPUExecutionProvider', 'technical_inference': 'passed',
            'scope': 'integrity and compatibility only; synthetic constant input does not measure field accuracy'}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    result = check_model(ROOT / 'models/semantic-v1')
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
