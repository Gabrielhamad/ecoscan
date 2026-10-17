"""Evaluate a fixed zero-shot recognizer with EcoScan preparation before inference."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import cv2
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, f1_score, confusion_matrix

from ecoscan.app.pipeline import default_processing_options, run_processing_pipeline
from ecoscan.classification.contrastive import ContrastiveClassifier, MODEL_NAME, PRETRAINED, PROMPTS, accepted_scores
from ecoscan.config import load_config
from ecoscan.image_processing.contracts import processing_contract


def metrics(labels, scores, classes, threshold, known_classes):
    predictions = np.asarray(classes)[scores.argmax(axis=1)]
    accepted = accepted_scores(scores, threshold, classes)
    return {'accuracy': float(accuracy_score(labels, predictions)),
            'macro_f1_known_classes': float(f1_score(labels, predictions, labels=known_classes, average='macro', zero_division=0)),
            'per_class': classification_report(labels, predictions, labels=classes, output_dict=True, zero_division=0),
            'confusion_matrix': confusion_matrix(labels, predictions, labels=classes).tolist(),
            'threshold': threshold, 'classes': classes, 'accepted_count': int(accepted.sum()),
            'coverage': float(accepted.mean()), 'unknown_count': int((predictions == 'unknown').sum()),
            'accepted_accuracy': float((predictions[accepted] == np.asarray(labels)[accepted]).mean()) if accepted.any() else None}


def main():
    import open_clip
    import torch

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--reference-run', type=Path, required=True)
    parser.add_argument('--cache-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a new report directory.')
    config = load_config()
    if set(config.classes) != set(PROMPTS) - {'unknown'}:
        raise ValueError('Prompt bank does not match configured material classes.')
    reference = json.loads((args.reference_run / 'training_summary.json').read_text(encoding='utf-8'))
    if reference['processing'] != processing_contract(config):
        raise ValueError('Reference preparation differs.')
    manifest_path = args.reference_run / 'dataset_manifest.json'
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != reference['manifest_sha256']:
        raise ValueError('Reference manifest changed.')
    records = [row for row in json.loads(manifest_path.read_text(encoding='utf-8')) if row['split'] in {'validation', 'test'}]
    source = args.source.resolve()
    groups = {}
    for row in records:
        path = (source / row['path']).resolve()
        if not path.is_relative_to(source) or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Reference image changed.')
        if row['group'] in groups and groups[row['group']] != row['split']:
            raise ValueError('Evaluation groups overlap.')
        groups[row['group']] = row['split']
    args.output.mkdir(parents=True)
    torch.set_num_threads(4)
    cv2.setNumThreads(2)
    classifier = ContrastiveClassifier(args.cache_dir)
    options = replace(default_processing_options(config), segmentation_name='none', morphology_name='none')
    scores, timings, evidence = [], [], []
    for index, row in enumerate(records):
        processed = run_processing_pipeline(source / row['path'], config, options)
        start = time.perf_counter()
        result = classifier.relative_scores(processed.recognition_image)
        timings.append(time.perf_counter() - start)
        scores.append(result)
        evidence.append({'path': row['path'], 'sha256': row['sha256'], 'split': row['split'],
                         'expected': row['class_id'], 'relative_scores': dict(zip(classifier.classes, map(float, result))),
                         'filter': processed.metadata['filter']})
        if (index + 1) % 25 == 0:
            print(f'Evaluated {index + 1}/{len(records)}', flush=True)
    matrix, labels = np.vstack(scores), np.array([row['class_id'] for row in records])
    val = np.array([row['split'] == 'validation' for row in records])
    test = ~val
    policies = [metrics(labels[val], matrix[val], classifier.classes, threshold, config.classes)
                for threshold in (.5, .6, .7, .8, .9, .95)]
    eligible = [policy for policy in policies if policy['accepted_count'] >= 20 and (policy['accepted_accuracy'] or 0) >= .9]
    threshold = max(eligible, key=lambda row: row['coverage'])['threshold'] if eligible else .95
    summary = {'architecture': MODEL_NAME, 'pretrained': PRETRAINED, 'source': classifier.source,
               'method': 'Fixed zero-shot text prototypes; no EcoScan gradient fitting.',
               'prompts': PROMPTS, 'prompts_sha256': hashlib.sha256(json.dumps(PROMPTS, sort_keys=True).encode()).hexdigest(),
               'processing': processing_contract(config), 'reference_manifest_sha256': reference['manifest_sha256'],
               'validation': metrics(labels[val], matrix[val], classifier.classes, threshold, config.classes),
               'test': metrics(labels[test], matrix[test], classifier.classes, threshold, config.classes),
               'validation_acceptance_target_met': bool(eligible),
               'inference_seconds_median': float(np.median(timings)),
               'environment': {'torch': torch.__version__, 'open_clip': open_clip.__version__},
               'score_kind': 'Relative softmax score, not calibrated disposal probability.',
               'limitations': ['Reference test reused: exploratory.', 'No verified unknown/background evaluation set.',
                               'Possible pretraining overlap cannot be excluded.', 'Not automatic object detection.'],
               'active_model_changed': False}
    if args.cases:
        with args.cases.open(encoding='utf-8-sig', newline='') as file:
            cases = list(csv.DictReader(file))
        summary['regression_cases'] = []
        for row in cases:
            processed = run_processing_pipeline((args.cases.parent / row['path']).resolve(), config)
            result = classifier.relative_scores(processed.recognition_image)
            predicted = classifier.classes[int(result.argmax())]
            summary['regression_cases'].append({'expected': row['expected_class'], 'predicted': predicted,
                'relative_score': float(result.max()), 'accepted': bool(accepted_scores(result[None], threshold, classifier.classes)[0])})
    summary['cached_weights'] = [{'name': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                                for path in args.cache_dir.rglob('*') if path.is_file() and path.suffix in {'.pt', '.bin', '.safetensors'}]
    (args.output / 'predictions.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({'test_accuracy': summary['test']['accuracy'], 'test_macro_f1': summary['test']['macro_f1_known_classes'],
                      'coverage': summary['test']['coverage'], 'accepted_accuracy': summary['test']['accepted_accuracy'],
                      'regression_cases': summary.get('regression_cases')}), flush=True)


if __name__ == '__main__':
    main()
