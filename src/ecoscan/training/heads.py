"""Supervised heads with train-only, group-aware probability calibration."""
from __future__ import annotations

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer, StandardScaler
from sklearn.svm import SVC


def calibration_folds(labels, groups, seed):
    labels, groups = np.asarray(labels), np.asarray(groups)
    if len(labels) != len(groups) or not len(labels):
        raise ValueError("Calibration labels and groups must be aligned.")
    classes = set(labels)
    if any(len(set(groups[labels == label])) < 5 for label in classes):
        raise ValueError("Calibration requires five training groups per class.")
    folds = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed).split(
        np.zeros(len(labels)), labels, groups))
    for train, held_out in folds:
        if set(groups[train]) & set(groups[held_out]):
            raise ValueError("Calibration groups overlap.")
        if set(labels[train]) != classes or set(labels[held_out]) != classes:
            raise ValueError("Calibration fold is missing a class.")
    return folds


def build_head(kind, c_value, labels, groups, seed):
    if kind == "logistic":
        return make_pipeline(StandardScaler(), LogisticRegression(
            C=c_value, class_weight="balanced", max_iter=2500, random_state=seed))
    if kind != "svm_calibrated":
        raise ValueError("Unknown classifier head.")
    estimator = make_pipeline(Normalizer(), SVC(
        C=c_value, kernel="rbf", gamma="scale", class_weight="balanced",
        random_state=seed))
    return CalibratedClassifierCV(estimator, method="sigmoid",
                                  cv=calibration_folds(labels, groups, seed), ensemble=False)
