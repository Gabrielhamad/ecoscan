import numpy as np
import pytest

from ecoscan.training.fixed_split import extend_reference_split, source_weights
from scripts.import_trashnet import MAPPING, is_near_copy, signature


def test_external_data_cannot_change_or_enter_reference_holdout():
    reference = [dict(path='metal/a.jpg', sha256='a', class_id='metal', split='test'),
                 dict(path='metal/b.jpg', sha256='b', class_id='metal', split='train')]
    records = reference + [dict(path='metal/web.jpg', sha256='c', class_id='metal')]
    assert extend_reference_split(records, [0, 1, 2], reference) == ['test', 'train', 'train']
    with pytest.raises(ValueError, match='held-out'):
        extend_reference_split(records, [0, 1, 0], reference)
    with pytest.raises(ValueError, match='different reference'):
        extend_reference_split(records, [0, 0, 1], reference)
    changed = [dict(records[0], sha256='changed'), *records[1:]]
    with pytest.raises(ValueError, match='changed'):
        extend_reference_split(changed, [0, 1, 2], reference)
    with pytest.raises(ValueError, match='missing'):
        extend_reference_split(records[1:], [1, 2], reference)


def test_public_source_mapping_and_near_copy_filter():
    assert MAPPING['paper'] == MAPPING['cardboard'] == 'paper_cardboard'
    assert 'trash' not in MAPPING and 'battery' not in MAPPING
    image = np.zeros((80, 120, 3), dtype=np.uint8)
    identity = signature(image)
    assert is_near_copy(identity, [identity])
    assert is_near_copy(('other', identity[1] ^ 1), [identity])
    assert not is_near_copy(('different', identity[1] ^ ((1 << 64) - 1)), [identity])


def test_source_weights_balance_classes_without_web_volume_domination():
    labels = np.array(['metal'] * 12 + ['battery'] * 2)
    external = np.array([False] * 2 + [True] * 10 + [False] * 2)
    weights = source_weights(labels, external, .25)
    assert weights.sum() == pytest.approx(4)
    assert weights[labels == 'metal'].sum() == pytest.approx(weights[labels == 'battery'].sum())
    assert weights[external].sum() / weights[(labels == 'metal') & ~external].sum() == pytest.approx(.25)
    with pytest.raises(ValueError, match='reference training'):
        source_weights(['metal'], [True], .25)
