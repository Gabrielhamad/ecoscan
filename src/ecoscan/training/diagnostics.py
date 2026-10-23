"""Explain the existing release gate without changing its acceptance criteria."""
from collections import Counter
from datetime import datetime, timezone


def evaluation_details(candidate, reference, classes, labels):
    reasons = []
    if candidate['macro_f1'] <= reference['macro_f1'] + .005:
        reasons.append({'code': 'macro_f1_gain_below_minimum'})
    comparison = {}
    for name in classes:
        new, old = candidate['by_class'][name], reference['by_class'][name]
        comparison[name] = {'support': new['support'], 'reference_recall': old['recall'],
                            'candidate_recall': new['recall']}
        if new['support'] < 10:
            reasons.append({'code': 'insufficient_validation', 'class_id': name})
        if new['recall'] < old['recall']:
            reasons.append({'code': 'recall_regression', 'class_id': name})
    if candidate['wrong_confident'] > reference['wrong_confident']:
        reasons.append({'code': 'more_confident_errors'})
    return {'evaluated_at': datetime.now(timezone.utc).isoformat(),
            'training_counts': dict(Counter(labels)), 'by_class': comparison,
            'reference_wrong_confident': reference['wrong_confident'],
            'candidate_wrong_confident': candidate['wrong_confident'],
            'validation_kind': 'historical_reused', 'gate_reasons': reasons}
