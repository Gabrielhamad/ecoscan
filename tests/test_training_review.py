import csv
import hashlib
import json

import numpy as np
import pytest

from ecoscan.training.review import reviewed_exclusions, fitting_split_mask
from ecoscan.image_processing.recognition_views import foreground_view


def test_visual_review_cannot_mutate_holdout_or_changed_images(tmp_path):
    index = tmp_path / 'index.csv'
    index.write_text('review_id,path,class_id,sha256\nmetal_001,metal/a.jpg,metal,original\n', encoding='utf-8')
    policy = tmp_path / 'review.json'
    policy.write_text(json.dumps({'review_index_sha256': hashlib.sha256(index.read_bytes()).hexdigest(),
                                 'exclude': {'metal_001': 'Not a target photograph'}}), encoding='utf-8')
    record = {'path': 'metal/a.jpg', 'class_id': 'metal', 'sha256': 'original', 'split': 'train'}
    assert 'metal/a.jpg' in reviewed_exclusions([record], index, policy)
    with pytest.raises(ValueError, match='training-only'):
        reviewed_exclusions([dict(record, split='test')], index, policy)
    with pytest.raises(ValueError, match='training-only'):
        reviewed_exclusions([dict(record, sha256='changed')], index, policy)
    index.write_text('changed', encoding='utf-8')
    with pytest.raises(ValueError, match='index changed'):
        reviewed_exclusions([record], index, policy)


def test_foreground_crop_preserves_rgb_and_falls_back_when_ambiguous():
    rgb = np.full((200, 300, 3), 220, dtype=np.uint8)
    rgb[40:160, 110:190] = [20, 80, 160]
    mask = np.zeros((200, 300), np.uint8)
    mask[40:160, 110:190] = 255
    view, evidence = foreground_view(rgb, mask)
    assert evidence['applied'] and view.shape == (224, 224, 3)
    left, top, right, bottom = evidence['box_xyxy']
    assert left < 110 and top < 40 and right > 190 and bottom > 160
    np.testing.assert_array_equal(view[112, 112], [20, 80, 160])
    _, full = foreground_view(rgb, np.full((200, 300), 255, dtype=np.uint8))
    assert not full['applied']
    _, empty = foreground_view(rgb, np.zeros((200, 300), dtype=np.uint8))
    assert not empty['applied']


def test_fine_tuning_excludes_reviewed_training_but_keeps_all_evaluation_images():
    records = [{'split': 'train', 'eligible_for_fit': False},
               {'split': 'train', 'eligible_for_fit': True},
               {'split': 'validation', 'eligible_for_fit': False},
               {'split': 'test', 'eligible_for_fit': False}]
    assert fitting_split_mask(records, 'train') == [False, True, False, False]
    assert fitting_split_mask(records, 'validation') == [False, False, True, False]
    assert fitting_split_mask(records, 'test') == [False, False, False, True]
    assert fitting_split_mask([{'split': 'train'}], 'train') == [True]
