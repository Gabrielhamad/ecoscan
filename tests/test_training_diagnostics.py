from ecoscan.training.diagnostics import evaluation_details
from ecoscan.training.semantic_learning import improvement


def report(f1=.7, recall=.8, support=20, errors=1):
    return {'macro_f1': f1, 'wrong_confident': errors,
            'by_class': {'metal': {'support': support, 'recall': recall}}}


def test_explains_all_rejection_conditions():
    old, new = report(), report(.6, .7, 3, 2)
    details = evaluation_details(new, old, ['metal'], ['metal', 'metal'])
    assert {r['code'] for r in details['gate_reasons']} == {
        'macro_f1_gain_below_minimum', 'recall_regression',
        'insufficient_validation', 'more_confident_errors'}
    assert details['training_counts'] == {'metal': 2}
    assert details['by_class']['metal']['support'] == 3


def test_passing_gate_has_no_reasons():
    old, new = report(), report(.8, .9)
    assert improvement(new, old, ['metal'])
    assert evaluation_details(new, old, ['metal'], ['metal'])['gate_reasons'] == []


def test_equal_model_is_not_an_improvement():
    assert evaluation_details(report(), report(), ['metal'], [])['gate_reasons'] == [
        {'code': 'macro_f1_gain_below_minimum'}]
