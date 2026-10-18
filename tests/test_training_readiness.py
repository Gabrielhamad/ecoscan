import pytest
from ecoscan.training.readiness import training_readiness


def test_holdouts_and_excluded_images_do_not_satisfy_training_minimum():
    rows = [{'class_id': 'metal', 'split': 'train', 'eligible_for_fit': False}] * 50
    rows += [{'class_id': 'metal', 'split': 'test'}] * 50
    rows += [{'class_id': 'metal', 'split': 'train'}] * 2
    result = training_readiness(rows, ['metal', 'glass'])
    assert not result['ready']
    assert result['insufficient_classes'] == {'metal': 2, 'glass': 0}


def test_counts_are_only_a_minimum_guard():
    result = training_readiness([{'class_id': 'metal', 'split': 'train'}] * 20, ['metal'])
    assert result['ready']
    assert 'do not establish' in result['note']


@pytest.mark.parametrize('minimum', [0, -1, True, 1.5])
def test_invalid_minimum_rejected(minimum):
    with pytest.raises(ValueError):
        training_readiness([], ['metal'], minimum)
