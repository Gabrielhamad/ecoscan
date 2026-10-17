import numpy as np
import pytest
from ecoscan.classification.selective_policy import fit_policy, apply_policy


def test_unsupported_class_and_unknown_abstain():
    classes = ['metal', 'glass', 'unknown']
    scores = np.array([[.9, .05, .05]] * 10 + [[.05, .9, .05], [.01, .01, .98]])
    policy = fit_policy(['metal'] * 10 + ['glass', 'unknown'], scores, classes)
    assert policy['glass'] is None
    assert apply_policy(scores, classes, policy).tolist() == [True] * 10 + [False, False]


def test_margin_blocks_ambiguous_prediction():
    scores = np.array([[.51, .49], [.9, .1]])
    assert apply_policy(scores, ['metal', 'glass'], {'metal': {'threshold': .5, 'margin': .2}}).tolist() == [False, True]


def test_no_eligible_policy_does_not_fall_back_to_guessing():
    scores = np.array([[.99, .01]] * 12)
    policy = fit_policy(['glass'] * 12, scores, ['metal', 'glass'])
    assert not apply_policy(scores, ['metal', 'glass'], policy).any()


def test_invalid_scores_fail_closed():
    with pytest.raises(ValueError):
        apply_policy(np.array([[float('nan'), .1]]), ['metal', 'glass'], {})
