"""Evaluate a trusted candidate on a reviewed CSV of real-world regressions."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ecoscan.app.pipeline import run_processing_pipeline
from ecoscan.classification.deep_features import DeepFeatureClassifier
from ecoscan.config import load_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--cases', type=Path, required=True, help='CSV: path,expected_class')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a new report path.')
    config = load_config()
    classifier = DeepFeatureClassifier.load(args.candidate, config)
    with args.cases.open(encoding='utf-8-sig', newline='') as file:
        cases = list(csv.DictReader(file))
    if not cases or any(row.get('expected_class') not in config.classes or not row.get('path') for row in cases):
        raise ValueError('Cases require an image path and a configured expected class.')
    results = []
    for row in cases:
        path = (args.cases.parent / row['path']).resolve()
        processed = run_processing_pipeline(path, config)
        prediction = classifier.predict_image(processed.recognition_image)
        results.append({
            'case': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'expected_class': row['expected_class'], 'predicted_class': prediction.top_class_id,
            'accepted': prediction.accepted, 'score': prediction.probability,
            'correct': prediction.top_class_id == row['expected_class'],
            'processing': processed.metadata,
        })
    report = {
        'model_sha256': hashlib.sha256((args.candidate / 'candidate.joblib').read_bytes()).hexdigest(),
        'cases': results, 'count': len(results),
        'correct': sum(row['correct'] for row in results),
        'accepted': sum(row['accepted'] for row in results),
        'wrong_accepted': sum(row['accepted'] and not row['correct'] for row in results),
        'purpose': 'Known regression cases, not an independent estimate of field accuracy.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('count', 'correct', 'accepted', 'wrong_accepted')}))


if __name__ == '__main__':
    main()
