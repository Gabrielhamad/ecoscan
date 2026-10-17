"""Apply explicit visual-review decisions to training eligibility, never labels."""
from __future__ import annotations

import csv
import hashlib
import json


def fitting_split_mask(records, split):
    if split not in {'train', 'validation', 'test'}:
        raise ValueError('Unknown dataset split.')
    if any(not isinstance(row.get('eligible_for_fit', True), bool) for row in records):
        raise ValueError('Training eligibility must be boolean.')
    return [row['split'] == split and (split != 'train' or row.get('eligible_for_fit', True))
            for row in records]


def reviewed_exclusions(records, index_path, decisions_path):
    policy = json.loads(decisions_path.read_text(encoding='utf-8'))
    if hashlib.sha256(index_path.read_bytes()).hexdigest() != policy['review_index_sha256']:
        raise ValueError('Review index changed; regenerate and review decisions.')
    with index_path.open(encoding='utf-8-sig', newline='') as file:
        rows = list(csv.DictReader(file))
    index = {row['review_id']: row for row in rows}
    data = {row['path']: row for row in records}
    if len(index) != len(rows):
        raise ValueError('Duplicate review identifiers.')
    excluded = {}
    for review_id, reason in policy['exclude'].items():
        if review_id not in index or not isinstance(reason, str) or not reason.strip():
            raise ValueError('Invalid review decision.')
        reviewed = index[review_id]
        current = data.get(reviewed['path'])
        if (current is None or current['sha256'] != reviewed['sha256']
                or current['class_id'] != reviewed['class_id'] or current['split'] != 'train'):
            raise ValueError('Review must match an unchanged training-only image.')
        if reviewed['path'] in excluded:
            raise ValueError('Duplicate reviewed image.')
        excluded[reviewed['path']] = {'review_id': review_id, 'reason': reason,
                                      'sha256': reviewed['sha256'], 'class_id': reviewed['class_id']}
    return excluded
