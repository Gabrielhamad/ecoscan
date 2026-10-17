"""Fit a reviewed supervised probe on fixed CLIP features and compare text priors."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

import cv2
import joblib
import numpy as np

from ecoscan.app.pipeline import default_processing_options, run_processing_pipeline
from ecoscan.classification.contrastive import ContrastiveClassifier, MODEL_NAME, PRETRAINED, PROMPTS, accepted_scores, aligned_probe_scores
from ecoscan.config import load_config
from ecoscan.image_processing.contracts import processing_contract
from ecoscan.training.heads import build_head
from ecoscan.training.review import fitting_split_mask
from scripts.evaluate_contrastive import metrics


align_probe_scores = aligned_probe_scores


def main():
    import torch
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--reference-run', type=Path, required=True)
    parser.add_argument('--cache-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=Path)
    args = parser.parse_args()
    config = load_config()
    if set(config.classes) != set(PROMPTS) - {'unknown'}:
        raise ValueError('Prompt bank does not match configured classes.')
    if args.output.exists():
        raise ValueError('Choose a new output directory.')
    reference = json.loads((args.reference_run / 'training_summary.json').read_text(encoding='utf-8'))
    manifest = args.reference_run / 'dataset_manifest.json'
    if (reference['processing'] != processing_contract(config)
            or hashlib.sha256(manifest.read_bytes()).hexdigest() != reference['manifest_sha256']):
        raise ValueError('Reference preparation or manifest changed.')
    records = [row for row in json.loads(manifest.read_text(encoding='utf-8'))
               if row['split'] != 'train' or row.get('eligible_for_fit', True)]
    source = args.source.resolve()
    assigned_groups = {}
    for row in records:
        path = (source / row['path']).resolve()
        if not path.is_relative_to(source) or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Source changed.')
        if row['group'] in assigned_groups and assigned_groups[row['group']] != row['split']:
            raise ValueError('Object groups cross dataset splits.')
        assigned_groups[row['group']] = row['split']
    args.output.mkdir(parents=True)
    torch.set_num_threads(4)
    cv2.setNumThreads(2)
    classifier = ContrastiveClassifier(args.cache_dir)
    options = replace(default_processing_options(config), segmentation_name='none', morphology_name='none')

    def extract(row):
        processed = run_processing_pipeline(source / row['path'], config, options)
        features = classifier.image_features(processed.recognition_image)
        return features, classifier.scores_from_features(features), processed.metadata['filter']

    features, priors, evidence = [], [], []
    with ThreadPoolExecutor(max_workers=4) as executor:
        for index, (feature, prior, applied_filter) in enumerate(executor.map(extract, records)):
            features.append(feature)
            priors.append(prior)
            evidence.append({'path': records[index]['path'], 'sha256': records[index]['sha256'],
                             'split': records[index]['split'], 'filter': applied_filter})
            if (index + 1) % 50 == 0:
                print(f'Prepared {index + 1}/{len(records)} reviewed/reference images', flush=True)
    matrix, priors = np.vstack(features), np.vstack(priors)
    targets = np.array([row['class_id'] for row in records])
    train = np.array(fitting_split_mask(records, 'train'))
    validation = np.array(fitting_split_mask(records, 'validation'))
    test = np.array(fitting_split_mask(records, 'test'))
    groups = np.array([row['group'] for row in records])
    candidates = []
    baseline = metrics(targets[validation], priors[validation], classifier.classes, .95, config.classes)
    candidates.append((baseline['macro_f1_known_classes'], 'zero_shot', None, 1., None))
    for c_value in (.01, .1, 1.):
        head = build_head('logistic', c_value, targets[train], groups[train], config.random_seed)
        head.fit(matrix[train], targets[train])
        probe = align_probe_scores(head, matrix[validation], classifier.classes)
        for prior_weight in (0., .5, .75):
            probabilities = prior_weight * priors[validation] + (1 - prior_weight) * probe
            report = metrics(targets[validation], probabilities, classifier.classes, .95, config.classes)
            candidates.append((report['macro_f1_known_classes'], 'supervised_mixture', c_value, prior_weight, head))
            print(f'Validated C={c_value}, semantic_weight={prior_weight}: F1={report["macro_f1_known_classes"]:.4f}', flush=True)
    score, method, c_value, prior_weight, head = max(candidates, key=lambda candidate: candidate[0])

    def combine(features, prior):
        if head is None:
            return prior
        return prior_weight * prior + (1 - prior_weight) * align_probe_scores(head, features, classifier.classes)

    probabilities = combine(matrix, priors)
    policies = [metrics(targets[validation], probabilities[validation], classifier.classes, threshold, config.classes)
                for threshold in (.5, .6, .7, .8, .9, .95)]
    eligible = [row for row in policies if row['accepted_count'] >= 20 and (row['accepted_accuracy'] or 0) >= .9]
    threshold = max(eligible, key=lambda row: row['coverage'])['threshold'] if eligible else .95
    model_path = args.output / 'contrastive_probe.joblib'
    metadata = {'method': method, 'head': head, 'prior_weight': prior_weight, 'threshold': threshold,
                'classes': classifier.classes, 'processing': processing_contract(config),
                'model_name': MODEL_NAME, 'pretrained': PRETRAINED, 'prompts': PROMPTS}
    joblib.dump(metadata, model_path)
    np.savez_compressed(args.output / 'features.npz', features=matrix, semantic_scores=priors)
    summary = {'selection': {'method': method, 'C': c_value, 'prior_weight': prior_weight,
                            'validation_macro_f1': score, 'fit_count': int(train.sum()),
                            'candidates': [{'validation_macro_f1': value, 'method': kind, 'C': c,
                                            'prior_weight': weight} for value, kind, c, weight, _ in candidates]},
               'validation': metrics(targets[validation], probabilities[validation], classifier.classes, threshold, config.classes),
               'test': metrics(targets[test], probabilities[test], classifier.classes, threshold, config.classes),
               'acceptance_target_met_on_validation': bool(eligible),
               'model_sha256': hashlib.sha256(model_path.read_bytes()).hexdigest(),
               'reference_manifest_sha256': reference['manifest_sha256'],
               'processing': processing_contract(config), 'active_model_changed': False,
               'limitations': ['Repeated exploratory test; not a blind acceptance.',
                               'No independent unknown/background test.', 'No localization or tracking.']}
    if args.cases:
        with args.cases.open(encoding='utf-8-sig', newline='') as file:
            cases = list(csv.DictReader(file))
        summary['regression_cases'] = []
        for row in cases:
            processed = run_processing_pipeline((args.cases.parent / row['path']).resolve(), config)
            feature = classifier.image_features(processed.recognition_image)
            prior = classifier.scores_from_features(feature)
            scores = combine(feature[None], prior[None])[0]
            predicted = classifier.classes[int(scores.argmax())]
            summary['regression_cases'].append({'expected': row['expected_class'], 'predicted': predicted,
                'relative_score': float(scores.max()), 'accepted': bool(accepted_scores(scores[None], threshold, classifier.classes)[0])})
    (args.output / 'preparation.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({'selection': summary['selection'], 'test_accuracy': summary['test']['accuracy'],
                      'coverage': summary['test']['coverage'], 'accepted_accuracy': summary['test']['accepted_accuracy'],
                      'regression_cases': summary.get('regression_cases')}), flush=True)


if __name__ == '__main__':
    main()
