"""Minimum-data guard before fitting a convolutional candidate."""
from collections import Counter

from ecoscan.training.review import fitting_split_mask


def training_readiness(records, classes, minimum=20):
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise ValueError('Minimum training count must be a positive integer.')
    mask = fitting_split_mask(records, 'train')
    counts = Counter(row['class_id'] for row, eligible in zip(records, mask) if eligible)
    insufficient = {label: counts[label] for label in classes if counts[label] < minimum}
    return {'ready': not insufficient, 'minimum_per_class': minimum,
            'training_counts': {label: counts[label] for label in classes},
            'insufficient_classes': insufficient,
            'note': 'Minimum counts alone do not establish label quality, diversity or validation readiness.'}
