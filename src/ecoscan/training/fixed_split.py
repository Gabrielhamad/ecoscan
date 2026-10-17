"""Add new training data without silently changing reference evaluation sets."""
from __future__ import annotations

import numpy as np


def source_weights(labels, external, ratio):
    """Balance classes and bound the total external contribution per class."""
    labels, external = np.asarray(labels), np.asarray(external, dtype=bool)
    if len(labels) != len(external) or not len(labels) or not 0 < ratio <= 1:
        raise ValueError('Invalid source balancing inputs.')
    weights = np.zeros(len(labels), dtype=float)
    for label in set(labels):
        local = (labels == label) & ~external
        web = (labels == label) & external
        if not local.any():
            raise ValueError('Every class requires reference training images.')
        mass = 1 + ratio if web.any() else 1
        weights[local] = 1 / (local.sum() * mass)
        if web.any():
            weights[web] = ratio / (web.sum() * mass)
    return weights * ((~external).sum() / weights.sum())


def extend_reference_split(records, groups, reference):
    if len(records) != len(groups):
        raise ValueError('Records and groups must be aligned.')
    old = {row['path']: row for row in reference}
    if len(old) != len(reference) or not set(old) <= {row['path'] for row in records}:
        raise ValueError('Reference entries are duplicated or missing.')
    assigned = {}
    for row, group in zip(records, groups, strict=True):
        if row['path'] not in old:
            continue
        original = old[row['path']]
        if (row['sha256'] != original['sha256'] or row['class_id'] != original['class_id']
                or original['split'] not in {'train', 'validation', 'test'}):
            raise ValueError('Reference image or label changed.')
        split = original['split']
        if group in assigned and assigned[group] != split:
            raise ValueError('New groups connect different reference splits.')
        assigned[group] = split
    for row, group in zip(records, groups, strict=True):
        if row['path'] not in old and assigned.get(group, 'train') != 'train':
            raise ValueError('Additional image overlaps held-out reference data.')
    return [assigned.get(group, 'train') for group in groups]
