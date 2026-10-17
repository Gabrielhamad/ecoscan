import numpy as np
import pytest
import json
from unittest.mock import patch

from ecoscan.classification.contrastive import PROMPTS, ContrastiveProbeClassifier, accepted_scores
from scripts.evaluate_contrastive import metrics
from scripts.train_contrastive_probe import align_probe_scores


def test_unknown_is_rejected_even_with_a_high_relative_score():
    scores = np.array([[.99, .01], [.01, .99], [.55, .45]])
    assert accepted_scores(scores, .8, ['metal', 'unknown']).tolist() == [True, False, False]
    for invalid in (np.array([[np.nan, 0]]), np.array([[.4, .4]]), np.array([[-.2, 1.2]])):
        with pytest.raises(ValueError):
            accepted_scores(invalid, .8, ['metal', 'unknown'])


def test_metrics_count_unknown_predictions_as_errors_and_do_not_inflate_known_macro_f1():
    result = metrics(['metal', 'glass'], np.array([[.1, .1, .8], [.1, .9, 0]]),
                     ['metal', 'glass', 'unknown'], .8, ['metal', 'glass'])
    assert result['accuracy'] == .5
    assert result['macro_f1_known_classes'] == .5
    assert result['unknown_count'] == 1 and result['accepted_count'] == 1
    assert result['accepted_accuracy'] == 1
    assert set(PROMPTS) == {'plastic', 'metal', 'glass', 'paper_cardboard', 'battery', 'electronic', 'unknown'}


def test_supervised_probabilities_align_with_semantic_class_order():
    class Head:
        classes_ = np.array(['glass', 'metal'])

        def predict_proba(self, features):
            return np.array([[.2, .8]])

    aligned = align_probe_scores(Head(), np.zeros((1, 512)), ['metal', 'unknown', 'glass'])
    np.testing.assert_allclose(aligned, [[.8, 0, .2]])
    assert aligned.sum() == pytest.approx(1)


def test_reusable_probe_applies_mixture_and_never_accepts_unknown():
    class Encoder:
        classes = ['glass', 'metal', 'unknown']

        def image_features(self, image):
            return np.zeros(512)

        def scores_from_features(self, features):
            return np.array([.01, .98, .01])

    classifier = ContrastiveProbeClassifier(Encoder(), {'method': 'zero_shot', 'head': None,
        'classes': Encoder.classes, 'prior_weight': 1, 'threshold': .8})
    assert classifier.predict_image(None).class_id == 'metal'
    classifier.encoder.scores_from_features = lambda feature: np.array([.01, .01, .98])
    prediction = classifier.predict_image(None)
    assert prediction.top_class_id == 'unknown' and not prediction.accepted


def test_probe_integrity_is_checked_before_deserialization(tmp_path):
    (tmp_path / 'contrastive_probe.joblib').write_bytes(b'changed model')
    (tmp_path / 'summary.json').write_text(json.dumps({'model_sha256': 'wrong'}), encoding='utf-8')
    with patch('joblib.load') as load:
        with pytest.raises(ValueError, match='integrity'):
            ContrastiveProbeClassifier.load(tmp_path, None, tmp_path)
        load.assert_not_called()
