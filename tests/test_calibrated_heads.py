import numpy as np
import pytest

from ecoscan.training.heads import build_head, calibration_folds


def test_calibration_keeps_object_views_in_one_fold_and_requires_classes():
    labels = np.repeat(['metal', 'glass'], 30)
    groups = np.repeat(np.arange(30), 2)
    for train, held in calibration_folds(labels, groups, 42):
        assert not set(groups[train]) & set(groups[held])
        assert set(labels[train]) == set(labels[held]) == {'metal', 'glass'}
    with pytest.raises(ValueError, match='five training groups'):
        calibration_folds(labels, [0] * 60, 42)


def test_nonlinear_head_produces_valid_class_probabilities_after_serialization(tmp_path):
    import joblib
    rng = np.random.default_rng(42)
    labels = np.repeat(['glass', 'metal'], 30)
    features = rng.normal(0, .1, (60, 8))
    features[:30, :4] += 2
    features[30:, 4:] += 2
    head = build_head('svm_calibrated', 1, labels, np.arange(60), 42)
    head.fit(features, labels)
    probabilities = head.predict_proba(features)
    assert np.isfinite(probabilities).all()
    np.testing.assert_allclose(probabilities.sum(axis=1), 1)
    assert (head.predict(features) == labels).mean() > .95
    path = tmp_path / 'head.joblib'
    joblib.dump(head, path)
    np.testing.assert_allclose(joblib.load(path).predict_proba(features), probabilities)
    assert head.n_features_in_ == 8
