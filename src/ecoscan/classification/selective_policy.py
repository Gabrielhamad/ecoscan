"""Validation-only selective classification; abstention is not accuracy."""
from __future__ import annotations

import numpy as np

from ecoscan.classification.contrastive import accepted_scores


def apply_policy(scores, classes, policy):
    scores = np.asarray(scores)
    accepted_scores(scores, 1, classes)  # Validate distributions before decisions.
    ordered = np.sort(scores, axis=1)
    margin = ordered[:, -1] - ordered[:, -2]
    predicted = np.asarray(classes)[scores.argmax(axis=1)]
    accepted = np.zeros(len(scores), dtype=bool)
    for label in classes:
        rule = policy.get(label)
        if label == 'unknown' or rule is None:
            continue
        threshold, minimum_margin = rule['threshold'], rule['margin']
        if not 0 < threshold <= 1 or not 0 <= minimum_margin <= 1:
            raise ValueError('Invalid selective rule.')
        accepted |= ((predicted == label) & (scores.max(axis=1) >= threshold)
                     & (margin >= minimum_margin))
    return accepted


def fit_policy(labels, scores, classes, *, min_support=10, target_precision=.95):
    """Caller must supply validation only, never test or fitting examples."""
    labels = np.asarray(labels)
    if min_support < 1 or not 0 < target_precision <= 1 or len(labels) != len(scores):
        raise ValueError('Invalid validation policy inputs.')
    accepted_scores(scores, 1, classes)
    predicted = np.asarray(classes)[scores.argmax(axis=1)]
    policy = {}
    for label in classes:
        best = None
        if label == 'unknown':
            continue
        for threshold in (.5, .6, .7, .8, .9, .95):
            for margin in (0., .1, .2, .3):
                rule = {'threshold': threshold, 'margin': margin}
                mask = apply_policy(scores, classes, {label: rule})
                count = int(mask.sum())
                precision = float((predicted[mask] == labels[mask]).mean()) if count else 0.
                if count >= min_support and precision >= target_precision:
                    if best is None or count > best['validation_count']:
                        best = dict(rule, validation_count=count, validation_precision=precision)
        policy[label] = best
    return policy


def selective_metrics(labels, scores, classes, accepted):
    labels = np.asarray(labels)
    predicted = np.asarray(classes)[scores.argmax(axis=1)]
    correct = predicted == labels
    return {'total': len(labels), 'accepted': int(accepted.sum()),
            'wrong_accepted': int((accepted & ~correct).sum()),
            'coverage': float(accepted.mean()),
            'accepted_precision': float(correct[accepted].mean()) if accepted.any() else None,
            'classification_accuracy': float(correct.mean())}
