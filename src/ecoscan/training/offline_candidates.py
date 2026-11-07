"""Fixed-grid heads and validation-only calibration; never imported by the web runtime."""
from __future__ import annotations

from copy import deepcopy
from typing import Any
from time import perf_counter

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from ecoscan.classification.semantic_onnx import SemanticOnnxClassifier, softmax
from ecoscan.metrics.classification_metrics import classification_report

SEED = 42
REGULARIZATION = (.01, .1, 1.0)
TEMPERATURES = (.75, 1.0, 1.5, 2.0)
THRESHOLDS = (.5, .6, .7, .8, .9, .95, 1.0)


def head_model(arrays: dict[str, np.ndarray], metadata: dict[str, Any]) -> SemanticOnnxClassifier:
    model = SemanticOnnxClassifier.__new__(SemanticOnnxClassifier)
    model.arrays, model.metadata, model.classes = arrays, metadata, metadata['classes']
    return model


def fit_candidate(base: SemanticOnnxClassifier, features: np.ndarray, labels: list[str],
                  c: float, balanced: bool) -> SemanticOnnxClassifier:
    if len(set(labels)) < 2:
        raise ValueError('At least two training classes are required')
    scaler = StandardScaler().fit(features)
    with threadpool_limits(limits=1):
        head = LogisticRegression(C=c, class_weight='balanced' if balanced else None,
                                  max_iter=2500, random_state=SEED).fit(scaler.transform(features), labels)
    if max(head.n_iter_) >= 2500:
        raise ValueError('Head did not converge')
    coef, intercept = head.coef_, head.intercept_
    if len(head.classes_) == 2:
        coef, intercept = np.vstack([-coef / 2, coef / 2]), np.r_[-intercept / 2, intercept / 2]
    arrays = deepcopy(base.arrays)
    arrays.update(mean=scaler.mean_, scale=scaler.scale_, coef=coef, intercept=intercept)
    return head_model(arrays, {**base.metadata, 'head_classes': head.classes_.tolist()})


def probabilities(model: SemanticOnnxClassifier, features: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    scores = np.array([[p.probabilities[c] for c in model.classes]
                       for p in [model.predict_features(feature) for feature in features]])
    if temperature == 1.0:
        return scores
    return np.array([softmax(np.log(np.clip(row, 1e-12, 1)) / temperature) for row in scores])


def validation_partition(rows: list[dict[str, Any]], minimum: int) -> tuple[list[int], list[int]]:
    """Connected components of object/session prevent leakage inside validation too."""
    groups: list[set[str]] = []
    for row in rows:
        component = {'o:' + row['object_id'], 's:' + row['session_id']}
        connected = [g for g in groups if g & component]
        for group in connected:
            component |= group
            groups.remove(group)
        groups.append(component)
    groups.sort(key=lambda g: sorted(g))
    order = np.random.default_rng(SEED).permutation(len(groups))
    calibration_nodes = set().union(*(groups[i] for i in order[:len(order) // 2]))
    cal = [i for i, r in enumerate(rows) if 'o:' + r['object_id'] in calibration_nodes]
    selection = [i for i in range(len(rows)) if i not in cal]
    classes = {r['class_id'] for r in rows}
    for subset in (cal, selection):
        if any(len({rows[i]['object_id'] for i in subset if rows[i]['class_id'] == c}) < minimum for c in classes):
            return [], list(range(len(rows)))
    return cal, selection


def calibrate(model: SemanticOnnxClassifier, x: np.ndarray, rows: list[dict[str, Any]], minimum: int) -> dict[str, Any]:
    labels = [model.classes.index(r['class_id']) for r in rows]
    losses = []
    for temperature in TEMPERATURES:
        scores = probabilities(model, x, temperature)
        losses.append(float(-np.log(np.clip(scores[np.arange(len(labels)), labels], 1e-12, 1)).mean()))
    temperature = TEMPERATURES[int(np.argmin(losses))]
    scores = probabilities(model, x, temperature)
    top, confidence = scores.argmax(axis=1), scores.max(axis=1)
    thresholds = {}
    for c in model.classes:
        if c == 'unknown':
            continue
        chosen = None  # No supported precision threshold means abstention for this class.
        for cutoff in THRESHOLDS:
            indices = [i for i in range(len(rows)) if top[i] == model.classes.index(c) and confidence[i] >= cutoff]
            if (len({rows[i]['object_id'] for i in indices}) >= minimum
                    and sum(rows[i]['class_id'] == c for i in indices) / len(indices) >= .95):
                chosen = cutoff
                break
        thresholds[c] = chosen
    return {'temperature': temperature, 'thresholds': thresholds, 'calibration_nll': min(losses)}


def evaluate_candidate(model: SemanticOnnxClassifier, x: np.ndarray, rows: list[dict[str, Any]],
                       rule: dict[str, Any]) -> dict[str, Any]:
    # Same frozen embeddings for baseline and candidates; encoder cost is shared.
    started = perf_counter()
    scores = probabilities(model, x, rule['temperature'])
    head_ms = (perf_counter() - started) * 1000 / len(rows)
    labels = [r['class_id'] for r in rows]
    top = [model.classes[int(i)] for i in scores.argmax(axis=1)]
    confidence = scores.max(axis=1)
    accepted = [c if c != 'unknown' and rule['thresholds'].get(c) is not None
                and p >= rule['thresholds'][c] else None for c, p in zip(top, confidence, strict=True)]
    total, count = len(rows), sum(c is not None for c in accepted)
    wrong = sum(c is not None and c != y for c, y in zip(accepted, labels, strict=True))
    severe = {'plastic_glass_swap': 0, 'hazard_to_regular': 0, 'out_of_scope_accepted': 0}
    accepted_by_class = {}
    for c in model.classes:
        predicted = sum(v == c for v in accepted)
        correct = sum(y == c and v == c for y, v in zip(labels, accepted, strict=True))
        references = labels.count(c)
        accepted_by_class[c] = {'count': predicted, 'correct': correct,
                                'precision': correct / predicted if predicted else None,
                                'coverage': sum(y == c and v is not None for y, v in zip(labels, accepted, strict=True)) / references if references else 0.0}
    for y, c in zip(labels, accepted, strict=True):
        severe['plastic_glass_swap'] += int(c is not None and y != c and {y, c} == {'plastic', 'glass'})
        severe['hazard_to_regular'] += int(y in {'battery', 'electronic'} and c in {'plastic', 'glass', 'metal', 'paper_cardboard'})
        severe['out_of_scope_accepted'] += int(y == 'unknown' and c is not None)
    return {'top1': classification_report(labels, top, model.classes),
            'coverage': count / total, 'accepted_precision': (count - wrong) / count if count else None,
            'accepted': count, 'wrong_accepted': wrong, 'severe_confusions': severe,
            'accepted_by_class': accepted_by_class,
            'head_ms_per_image': head_ms, 'weights_bytes': sum(a.nbytes for a in model.arrays.values()),
            'support': {c: {'objects': len({r['object_id'] for r in rows if r['class_id'] == c}),
                            'sessions': len({r['session_id'] for r in rows if r['class_id'] == c})} for c in model.classes}}


def gate(candidate: dict[str, Any], baseline: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    reasons = []
    if candidate['top1']['macro_f1'] <= baseline['top1']['macro_f1'] + policy['macro_f1_gain']:
        reasons.append('insufficient_macro_f1_gain')
    for c, support in candidate['support'].items():
        if support['objects'] < policy['minimum_objects_per_class'] or support['sessions'] < policy['minimum_sessions_per_class']:
            reasons.append('insufficient_support:' + c)
        if candidate['top1']['by_class'][c]['recall'] + policy['max_recall_drop'] < baseline['top1']['by_class'][c]['recall']:
            reasons.append('recall_regression:' + c)
        accepted, reference = candidate['accepted_by_class'][c], baseline['accepted_by_class'][c]
        if accepted['count'] and accepted['precision'] < max(policy['minimum_accepted_precision'], reference['precision'] or 0):
            reasons.append('accepted_precision_regression:' + c)
        if accepted['coverage'] + policy['max_coverage_drop'] < reference['coverage']:
            reasons.append('accepted_coverage_regression:' + c)
    precision = candidate['accepted_precision']
    if precision is None or precision < max(policy['minimum_accepted_precision'], baseline['accepted_precision'] or 0):
        reasons.append('accepted_precision_regression_or_insufficient')
    if candidate['accepted'] < policy['minimum_accepted']:
        reasons.append('insufficient_accepted_support')
    if candidate['coverage'] + policy['max_coverage_drop'] < baseline['coverage']:
        reasons.append('coverage_regression')
    if candidate['wrong_accepted'] > baseline['wrong_accepted']:
        reasons.append('more_confident_errors')
    if any(candidate['severe_confusions'][k] > baseline['severe_confusions'][k] for k in baseline['severe_confusions']):
        reasons.append('severe_confusion_regression')
    if candidate['head_ms_per_image'] > baseline['head_ms_per_image'] * policy['max_head_latency_ratio'] + policy['head_latency_allowance_ms']:
        reasons.append('head_latency_regression')
    return reasons
