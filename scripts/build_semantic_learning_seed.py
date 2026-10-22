"""Package public-reference features only; never include citizen report photos."""
import hashlib
import json
from pathlib import Path
import numpy as np


def main():
    root = Path(__file__).resolve().parents[1]
    run = root / 'reports/recognition_semantic_20261022'
    summary = json.loads((run / 'summary.json').read_text())
    manifest = next(p for p in (root / 'reports').glob('*/dataset_manifest.json')
                    if hashlib.sha256(p.read_bytes()).hexdigest() == summary['reference_manifest_sha256'])
    rows = [r for r in json.loads(manifest.read_text())
            if r['split'] != 'train' or r.get('eligible_for_fit', True)]
    evidence = json.loads((run / 'preparation.json').read_text())
    if [(r['path'], r['sha256'], r['split']) for r in rows] != [
            (r['path'], r['sha256'], r['split']) for r in evidence]:
        raise ValueError('Feature provenance mismatch')
    groups = {}
    for row in rows:
        if row['group'] in groups and groups[row['group']] != row['split']:
            raise ValueError('Capture group crosses splits')
        groups[row['group']] = row['split']
    folder = root / 'models/semantic-v1'
    metadata = json.loads((folder / 'semantic.json').read_text())
    with np.load(run / 'features.npz', allow_pickle=False) as data:
        features = data['features']
    masks = {split: np.array([r['split'] == split for r in rows]) for split in ('train', 'validation')}
    labels = np.array([r['class_id'] for r in rows])
    output = folder / 'learning_seed.npz'
    if output.exists():
        raise ValueError('Seed already exists; version any replacement explicitly')
    np.savez_compressed(output, **{f'{split}_{kind}': values[mask]
        for split, mask in masks.items() for kind, values in [('x', features), ('y', labels)]})
    evidence = dict(sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                    processing=metadata['processing'], encoder_sha256=metadata['encoder_sha256'],
                    manifest_sha256=summary['reference_manifest_sha256'],
                    validation_hashes=[r['sha256'] for r in rows if r['split'] == 'validation'],
                    source='Reviewed public reference and TACO features; no citizen reports',
                    evaluation='Historical reused validation; assisted predictions only',
                    counts={split: int(mask.sum()) for split, mask in masks.items()})
    (folder / 'learning_seed.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(evidence['counts']))


if __name__ == '__main__':
    main()
