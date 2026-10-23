"""Train on reviewed web objects; reserve new scenes before fitting any head."""
import argparse
from collections import Counter
from copy import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ecoscan.app.pipeline import default_processing_options, run_processing_pipeline
from ecoscan.classification.semantic_onnx import SemanticOnnxClassifier
from ecoscan.config import load_config
from ecoscan.training.semantic_learning import fit_head, evaluate, improvement


def scene_split(group):
    return 'test' if int(hashlib.sha256(group.encode()).hexdigest()[:8], 16) % 5 == 0 else 'train'


def validate_batch_hashes(rows, metadata):
    previous = set(metadata.get('training_hashes', []))
    held_out = set(metadata.get('validation_hashes', []) + metadata.get('held_out_hashes', []))
    hashes = [row['sha256'] for row in rows]
    if len(set(hashes)) != len(hashes):
        raise ValueError('Duplicate image hashes in reviewed batch')
    if set(hashes) & (previous | held_out):
        raise ValueError('Reviewed image already belongs to training or evaluation')


def batch_sources(rows):
    sources = set()
    for row in rows:
        if 'taco_image_id' in row:
            sources.add('https://github.com/pedropro/TACO')
        elif row.get('source_archive_sha256') and row.get('archive_entry'):
            sources.add(row['source_url'])
        else:
            raise ValueError('Missing supported dataset provenance')
    return sorted(sources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewed', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose an unused experiment output')
    config = load_config()
    base_dir = config.directories['models'] / 'semantic-v1'
    base = SemanticOnnxClassifier(base_dir / 'semantic.json')
    seed_metadata = json.loads((base_dir / 'learning_seed.json').read_text())
    if hashlib.sha256((base_dir / 'learning_seed.npz').read_bytes()).hexdigest() != seed_metadata['sha256']:
        raise ValueError('Seed changed')
    if seed_metadata['processing'] != base.metadata['processing']:
        raise ValueError('Preparation mismatch')
    with np.load(base_dir / 'learning_seed.npz', allow_pickle=False) as data:
        seed = {k: data[k] for k in data.files}
    rows = json.loads((args.reviewed / 'manifest.json').read_text())
    previous_hashes = set(seed_metadata.get('training_hashes', []))
    validate_batch_hashes(rows, seed_metadata)
    sources = batch_sources(rows)
    options = replace(default_processing_options(config), segmentation_name='none', morphology_name='none')
    features = []
    for index, row in enumerate(rows):
        path = (args.reviewed / row['path']).resolve()
        if (not path.is_relative_to(args.reviewed.resolve()) or not row.get('eligible_for_fit')
                or row.get('review_method') != 'assistant_visual_review'
                or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']):
            raise ValueError('Unreviewed or changed image')
        row['split'] = scene_split(row['group'])
        processed = run_processing_pipeline(path, config, options)
        row['filter_used'] = processed.filter_result.name
        row['recognition_rgb_sha256'] = hashlib.sha256(processed.recognition_image.tobytes()).hexdigest()
        features.append(base.image_features(processed.recognition_image))
        print(f'Prepared {index+1}/{len(rows)}', flush=True)
    x = np.vstack(features)
    y = np.array([r['class_id'] for r in rows])
    train = np.array([r['split'] == 'train' for r in rows])
    if not train.any() or train.all():
        raise ValueError('Both new train and test scenes required')
    all_x = np.vstack([seed['train_x'], x[train]])
    all_y = np.concatenate([seed['train_y'], y[train]])
    arrays, head_classes = fit_head(base, all_x, all_y)
    candidate = copy(base)
    candidate.arrays = arrays
    candidate.metadata = {**base.metadata, 'head_classes': head_classes}
    # Fixed hyperparameters: validation is a promotion gate, never fitted.
    reports = {}
    for name, model in [('baseline', base), ('candidate', candidate)]:
        reports[name] = {
            'validation': evaluate(model, seed['validation_x'], seed['validation_y'], config.classes),
            'new_scene_test': evaluate(model, x[~train], y[~train], config.classes)}
    historical_run = ROOT / 'reports/recognition_semantic_20261022'
    evidence = json.loads((historical_run / 'preparation.json').read_text())
    mask = np.array([r['split'] == 'test' for r in evidence])
    manifest_hash = json.loads((historical_run / 'summary.json').read_text())['reference_manifest_sha256']
    manifest = next(p for p in (ROOT / 'reports').glob('*/dataset_manifest.json')
                    if hashlib.sha256(p.read_bytes()).hexdigest() == manifest_hash)
    reference = [r for r in json.loads(manifest.read_text())
                 if r['split'] != 'train' or r.get('eligible_for_fit', True)]
    if [(r['path'], r['sha256']) for r in reference] != [(r['path'], r['sha256']) for r in evidence]:
        raise ValueError('Historical feature provenance mismatch')
    with np.load(historical_run / 'features.npz', allow_pickle=False) as data:
        test_x = data['features'][mask]
    test_y = np.array([r['class_id'] for r in reference])[mask]
    for name, model in [('baseline', base), ('candidate', candidate)]:
        reports[name]['historical_test'] = evaluate(model, test_x, test_y, config.classes)
    before, after = reports['baseline']['validation'], reports['candidate']['validation']
    passed = (improvement(after, before, config.classes)
              and after['wrong_confident'] <= before['wrong_confident'])
    args.output.mkdir(parents=True)
    np.savez_compressed(args.output / 'head.npz', **arrays)
    metadata = {**candidate.metadata, 'head_sha256': hashlib.sha256((args.output / 'head.npz').read_bytes()).hexdigest()}
    (args.output / 'semantic.json').write_text(json.dumps(metadata, indent=2))
    np.savez_compressed(args.output / 'web_features.npz', features=x, labels=y, train=train)
    np.savez_compressed(args.output / 'learning_seed.npz', train_x=all_x, train_y=all_y,
                        validation_x=seed['validation_x'], validation_y=seed['validation_y'])
    expanded_seed = {**seed_metadata,
        'sha256': hashlib.sha256((args.output / 'learning_seed.npz').read_bytes()).hexdigest(),
        'counts': {'train': len(all_y), 'validation': len(seed['validation_y'])},
        'training_hashes': sorted(previous_hashes | {r['sha256'] for r in rows if r['split'] == 'train'}),
        'held_out_hashes': seed_metadata.get('held_out_hashes', []) + [r['sha256'] for r in rows if r['split'] == 'test'],
        'expansion': {'sources': sources,
                      'review_manifest_sha256': hashlib.sha256((args.reviewed / 'manifest.json').read_bytes()).hexdigest(),
                      'new_training_images': int(train.sum()),
                      'held_out_images': int((~train).sum())}}
    expanded_seed['expansions'] = seed_metadata.get('expansions',
        [seed_metadata['expansion']] if seed_metadata.get('expansion') else []) + [expanded_seed['expansion']]
    (args.output / 'learning_seed.json').write_text(json.dumps(expanded_seed, indent=2))
    (args.output / 'manifest.json').write_text(json.dumps(rows, indent=2))
    report = {'new_train': dict(Counter(y[train])), 'new_test': dict(Counter(y[~train])),
              'models': reports, 'validation_gate_passed': passed, 'production_changed': False,
              'limitations': ['Historical validation/test reused; new test consists of crops, not phone scenes.',
                              'No new battery or electronic photos in this round.',
                              'Scene separation does not prove distinct physical object identity.']}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
