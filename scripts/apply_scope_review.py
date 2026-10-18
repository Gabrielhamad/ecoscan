"""Create a corrected manifest from hash-bound exclusions; preserve held-out rows."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ecoscan.training.review import reviewed_exclusions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'index', 'decisions', 'source', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    records = json.loads(args.manifest.read_text(encoding='utf-8'))
    exclusions = reviewed_exclusions(records, args.index, args.decisions)
    source = args.source.resolve()
    corrected = []
    for record in records:
        path = (source / record['path']).resolve()
        if not path.is_relative_to(source) or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Source changed.')
        row = dict(record)
        if row['split'] == 'train':
            row['eligible_for_fit'] = record.get('eligible_for_fit', True) and row['path'] not in exclusions
            if row['path'] in exclusions:
                row['scope_review_exclusion'] = exclusions[row['path']]
        corrected.append(row)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'dataset_manifest.json').write_text(json.dumps(corrected, indent=2), encoding='utf-8')
    counts = Counter(r['class_id'] for r in corrected if r['split'] == 'train' and r['eligible_for_fit'])
    report = {'source_root': str(source), 'source_manifest_sha256': hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
              'training_eligible_counts': dict(counts), 'excluded_count': len(exclusions),
              'validation_test_unchanged': [r for r in records if r['split'] != 'train'] == [r for r in corrected if r['split'] != 'train'],
              'note': 'Remaining common materials need object-level review. Not a fully approved objects-v1 dataset.'}
    (args.output / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
