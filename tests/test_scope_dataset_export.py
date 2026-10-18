import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scripts import review_scope_dataset as export


def test_reference_scene_is_excluded_even_with_different_pixels(tmp_path, monkeypatch):
    source = tmp_path / 'reference'
    source.mkdir()
    incoming = tmp_path / 'incoming'
    incoming.mkdir()
    rng = np.random.default_rng(42)
    reference = source / 'plastic_0001_taco_13_1_bottle.png'
    Image.fromarray(rng.integers(0, 256, (100, 100, 3), dtype=np.uint8)).save(reference)
    original_hash = export.sha(reference)
    rows = []
    for index, scene in enumerate((13, 14)):
        path = incoming / f'{index}.png'
        Image.fromarray(rng.integers(0, 256, (100, 100, 3), dtype=np.uint8)).save(path)
        rows.append({'local_path': path.relative_to(tmp_path).as_posix(), 'class_id': 'plastic',
                     'sha256': export.sha(path), 'taco_image_id': scene})
    capture = incoming / 'capture.json'
    capture.write_text(json.dumps(rows))
    for name in ('source_config.json', 'source_annotations.json'):
        (incoming / name).write_text('{}')
    manifest = tmp_path / 'reference.json'
    manifest.write_text(json.dumps([{'path': reference.name, 'sha256': export.sha(reference), 'split': 'test'}]))
    decisions = tmp_path / 'decisions.json'
    decisions.write_text(json.dumps({'capture_sha256': export.sha(capture),
                                    'approved': {'taco_001': 'pet_bottle', 'taco_002': 'pet_bottle'}}))
    output = tmp_path / 'output'
    monkeypatch.setattr(export, 'ROOT', tmp_path)
    # Import the existing deduplication helper before substituting the script root.
    monkeypatch.syspath_prepend(str(Path(export.__file__).parent))
    monkeypatch.setattr(sys, 'argv', ['review', '--capture', str(capture), '--output', str(output),
                                   '--source', str(source), '--reference', str(manifest), '--decisions', str(decisions)])
    export.main()
    result = json.loads((output / 'manifest.json').read_text())
    summary = json.loads((output / 'summary.json').read_text())
    assert len(result) == 1
    assert result[0]['group'] == 'taco_image_14'
    assert result[0]['split'] == 'train'
    assert summary['not_exported'][0]['reason'] == 'same_source_scene_as_reference'
    assert export.sha(reference) == original_hash
