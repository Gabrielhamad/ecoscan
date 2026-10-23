"""Prespecified validation-only ablation; never deploy or inspect test labels."""
import argparse
from collections import Counter
from copy import copy, deepcopy
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ecoscan.classification.semantic_onnx import SemanticOnnxClassifier
from ecoscan.config import load_config
from ecoscan.training.semantic_learning import evaluate, fit_head, improvement


def fit_fixed_scaler(base, features, labels):
    if set(labels) != set(base.metadata['head_classes']):
        raise ValueError('Training classes differ from base')
    arrays = deepcopy(base.arrays)
    if not np.isfinite(arrays['scale']).all() or (arrays['scale'] <= 0).any():
        raise ValueError('Invalid base scale')
    head = LogisticRegression(C=.1, class_weight='balanced', max_iter=2500, random_state=42)
    head.fit((features - arrays['mean']) / arrays['scale'], labels)
    arrays.update(coef=head.coef_, intercept=head.intercept_)
    return arrays, list(head.classes_)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a new output path')
    config = load_config()
    base = SemanticOnnxClassifier(config.directories['models'] / 'semantic-v1/semantic.json')
    meta = json.loads(args.seed.with_suffix('.json').read_text())
    digest = hashlib.sha256(args.seed.read_bytes()).hexdigest()
    if (digest != meta['sha256'] or meta['processing'] != base.metadata['processing']
            or meta['encoder_sha256'] != base.metadata['encoder_sha256']):
        raise ValueError('Incompatible or changed seed')
    with np.load(args.seed, allow_pickle=False) as seed:
        x, y = seed['train_x'], seed['train_y']
        vx, vy = seed['validation_x'], seed['validation_y']
    candidates = {'published': base}
    prior = copy(base)
    prior.metadata = {**base.metadata, 'prior_weight': 1.0}
    candidates['pretrained_only'] = prior
    for name, fit in [('refit_scaler', fit_head), ('fixed_scaler', fit_fixed_scaler)]:
        model = copy(base)
        model.arrays, classes = fit(base, x, y)
        model.metadata = {**base.metadata, 'head_classes': classes}
        candidates[name] = model
    results = {name: evaluate(model, vx, vy, config.classes) for name, model in candidates.items()}
    baseline = results['published']
    report = {'training_counts': dict(Counter(y)), 'seed_sha256': digest,
              'validation': results, 'eligible': {
                  name: improvement(result, baseline, config.classes)
                  and result['wrong_confident'] <= baseline['wrong_confident']
                  for name, result in results.items() if name != 'published'},
              'test_used': False, 'production_changed': False,
              'limitations': ['Historical validation reused; independent field test still required.',
                              'Scores are not calibrated probabilities.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as file:
        json.dump(report, file, indent=2)
    print(json.dumps({'training_counts': report['training_counts'], 'eligible': report['eligible'],
                     'validation': {k: {'accuracy': v['accuracy'], 'macro_f1': v['macro_f1'],
                                       'wrong_confident': v['wrong_confident']} for k, v in results.items()}}, indent=2))


if __name__ == '__main__':
    main()
