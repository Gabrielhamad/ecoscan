from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from ecoscan.classification.deep_features import DeepFeatureClassifier, MobileNetFeatures, mobilenet_input
from ecoscan.training.grouped_split import grouped_split, image_groups
from scripts.train_deep_candidate import _capture_groups, _report


def test_backbone_preparation_preserves_rgb_channel_order():
    image = np.zeros((224, 224, 3), dtype=np.uint8)
    image[..., 0] = 255
    blob = mobilenet_input(image)
    assert blob.shape == (1, 3, 224, 224)
    np.testing.assert_allclose(blob[0, :, 0, 0], [(1 - .485) / .229, -.456 / .224, -.406 / .225], rtol=1e-6)
    with pytest.raises(ValueError):
        mobilenet_input(np.zeros((200, 200, 3), dtype=np.uint8))


def test_unverified_backbone_is_rejected_before_loading(tmp_path):
    weights = tmp_path / 'weights.onnx'
    weights.write_bytes(b'not the official network')
    with patch('cv2.dnn.readNetFromONNX') as load:
        with pytest.raises(ValueError, match='verified'):
            MobileNetFeatures(weights)
        load.assert_not_called()


def test_classifier_rejects_uncertain_and_invalid_probabilities():
    head, backbone = MagicMock(), MagicMock()
    head.classes_ = np.array(['glass', 'metal'])
    head.predict_proba.return_value = np.array([[.45, .55]])
    classifier = DeepFeatureClassifier(head, backbone, .8)
    prediction = classifier.predict_image(np.zeros((224, 224, 3), dtype=np.uint8))
    assert prediction.top_class_id == 'metal'
    assert prediction.class_id is None
    assert not prediction.accepted
    head.predict_proba.return_value = np.array([[np.nan, .9]])
    with pytest.raises(ValueError, match='probabilities'):
        classifier.predict_image(np.zeros((224, 224, 3), dtype=np.uint8))


def test_duplicate_and_capture_groups_stay_together():
    records = [
        {'class_id': 'metal', 'decoded_sha256': 'same', 'dhash': '0'},
        {'class_id': 'metal', 'decoded_sha256': 'same', 'dhash': '0'},
        {'class_id': 'metal', 'decoded_sha256': 'other', 'dhash': '1'},
        {'class_id': 'glass', 'decoded_sha256': 'third', 'dhash': 'ffffffffffffffff', 'capture_group': 'scene'},
        {'class_id': 'metal', 'decoded_sha256': 'fourth', 'dhash': 'abcdefabcdef', 'capture_group': 'scene'},
    ]
    groups = image_groups(records)
    assert groups[0] == groups[1] == groups[2]
    assert groups[3] == groups[4]
    records[1]['class_id'] = 'glass'
    with pytest.raises(ValueError, match='conflicting labels'):
        image_groups(records)


def test_grouped_split_never_leaks_or_drops_a_class():
    labels = ['metal'] * 30 + ['glass'] * 30
    groups = [i // 2 for i in range(60)]
    splits = grouped_split(labels, groups)
    assert splits == grouped_split(labels, groups)
    for group in set(groups):
        assert len({s for s, g in zip(splits, groups) if g == group}) == 1
    for split in ('train', 'validation', 'test'):
        assert {y for y, s in zip(labels, splits) if s == split} == {'metal', 'glass'}
    with pytest.raises(ValueError, match='five independent'):
        grouped_split(labels, [0] * len(labels))


def test_rejection_metrics_do_not_hide_wrong_or_rejected_answers():
    report = _report(['metal', 'glass'], np.array([[.6, .4], [.95, .05]]), ['metal', 'glass'], .9)
    assert report['coverage'] == .5
    assert report['accepted_accuracy'] == 0
    assert report['top1']['accuracy'] == .5
    rejected = _report(['metal'], np.array([[.6, .4]]), ['metal', 'glass'], .9)
    assert rejected['accepted_accuracy'] is None


def test_capture_manifest_does_not_accept_escape_or_duplicate_paths(tmp_path):
    manifest = tmp_path / 'groups.csv'
    manifest.write_text('path,group_id\n../outside.jpg,a\n', encoding='utf-8')
    with pytest.raises(ValueError, match='Invalid'):
        _capture_groups(manifest, tmp_path)
    manifest.write_text('path,group_id\na.jpg,a\na.jpg,b\n', encoding='utf-8')
    with pytest.raises(ValueError, match='duplicate'):
        _capture_groups(manifest, tmp_path)


def test_skipping_diagnostic_masks_keeps_exact_recognition_pixels(tmp_path):
    from dataclasses import replace
    from PIL import Image
    from ecoscan.app.pipeline import default_processing_options, run_processing_pipeline
    from ecoscan.config import load_config

    image = np.full((120, 180, 3), 210, dtype=np.uint8)
    image[25:100, 60:110] = [45, 130, 60]
    path = tmp_path / 'test.png'
    Image.fromarray(image).save(path)
    config = load_config()
    normal = default_processing_options(config)
    batch = replace(normal, segmentation_name='none', morphology_name='none')
    complete = run_processing_pipeline(path, config, normal)
    training = run_processing_pipeline(path, config, batch)
    np.testing.assert_array_equal(complete.recognition_image, training.recognition_image)
