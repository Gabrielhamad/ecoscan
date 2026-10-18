"""Apply the visual scope review to legacy training labels without deleting files."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', type=Path, required=True)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    previous = json.loads(args.previous.read_text(encoding='utf-8'))
    digest = hashlib.sha256(args.index.read_bytes()).hexdigest()
    if digest != previous['review_index_sha256']:
        raise ValueError('Legacy review index changed.')
    rows = list(csv.DictReader(args.index.open(encoding='utf-8-sig', newline='')))
    # Reviewed battery/electronic training contact sheets: retain only clear scope examples.
    approved = {'battery_010': 'household_cell', 'battery_011': 'household_cell',
                'electronic_040': 'mobile_phone'}
    excluded = dict(previous['exclude'])
    audited = Counter()
    for row in rows:
        if row['class_id'] not in {'battery', 'electronic'}:
            continue
        key = row['review_id']
        audited[row['class_id']] += 1
        if key not in approved and key not in excluded:
            excluded[key] = ('Outside objects-v1 or ambiguous on visual review: not a clearly '
                             'identifiable AA/AAA cell, mobile phone, computer mouse or wall charger. '
                             'Preserved for future review; not automatically relabeled as a negative.')
    if not set(approved).issubset({row['review_id'] for row in rows}):
        raise ValueError('Approved legacy ID missing.')
    result = {'review_index_sha256': digest, 'scope_version': 'objects-v1',
              'method': 'Assistant visual review of battery/electronic training contact sheets; conservative scope eligibility. Other materials retain previous decisions and still need object-level review.',
              'exclude': excluded, 'approved_object_labels': approved,
              'audited_training_counts': dict(audited), 'test_changed': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as file:
        json.dump(result, file, indent=2)
    print(json.dumps({'excluded_count': len(excluded), 'audited': dict(audited), 'approved_objects': approved}))


if __name__ == '__main__':
    main()
