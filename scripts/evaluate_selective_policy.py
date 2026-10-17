"""Audit cached contrastive predictions without retraining or test-set selection."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import joblib
import numpy as np
from ecoscan.classification.contrastive import aligned_probe_scores, accepted_scores
from ecoscan.classification.selective_policy import fit_policy, apply_policy, selective_metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads((args.run / 'summary.json').read_text())
    manifest = args.reference / 'dataset_manifest.json'
    model = args.run / 'contrastive_probe.joblib'
    if (hashlib.sha256(manifest.read_bytes()).hexdigest() != summary['reference_manifest_sha256']
            or hashlib.sha256(model.read_bytes()).hexdigest() != summary['model_sha256']):
        raise ValueError('Model or manifest changed.')
    rows = [r for r in json.loads(manifest.read_text()) if r['split'] != 'train' or r.get('eligible_for_fit', True)]
    evidence = json.loads((args.run / 'preparation.json').read_text())
    if [(r['path'], r['sha256'], r['split']) for r in rows] != [(r['path'], r['sha256'], r['split']) for r in evidence]:
        raise ValueError('Feature provenance does not match manifest.')
    payload = joblib.load(model)  # Trusted local training artifact, integrity checked above.
    arrays = np.load(args.run / 'features.npz', allow_pickle=False)
    classes = payload['classes']
    scores = arrays['semantic_scores']
    if payload['head'] is not None:
        weight = payload['prior_weight']
        scores = weight * scores + (1 - weight) * aligned_probe_scores(payload['head'], arrays['features'], classes)
    labels = np.array([r['class_id'] for r in rows])
    validation = np.array([r['split'] == 'validation' for r in rows])
    policy = fit_policy(labels[validation], scores[validation], classes)
    report = {'policy': policy, 'active_model_changed': False,
              'limitations': ['Repeated exploratory test, not independent.',
                             'No negative benchmark; no deployment approval.',
                             'Validation precision is not a statistical guarantee.']}
    for split in ('validation', 'test'):
        mask = np.array([r['split'] == split for r in rows])
        report[split] = {}
        for name, accepted in [('global', accepted_scores(scores[mask], payload['threshold'], classes)),
                               ('selective', apply_policy(scores[mask], classes, policy))]:
            report[split][name] = selective_metrics(labels[mask], scores[mask], classes, accepted)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
