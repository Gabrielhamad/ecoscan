"""Synthetic embeddings/images test the offline machinery, never field improvement."""
from copy import deepcopy
from dataclasses import replace
import importlib
import json
from unittest.mock import Mock

import numpy as np
from PIL import Image
import pytest

from ecoscan.config import load_config
from ecoscan.image_processing.contracts import processing_contract
from ecoscan.services.processing_evidence import array_digest
from ecoscan.classification.semantic_onnx import file_digest
from ecoscan.training import offline_experiment as experiment
from ecoscan.training.offline_data import AUGMENTATIONS, EmbeddingCache, audit_inputs
from ecoscan.training.offline_candidates import (
    calibrate, evaluate_candidate, fit_candidate, gate, head_model, probabilities, validation_partition,
)


def model_fixture():
    classes = ['glass', 'metal', 'unknown']
    arrays = {'prototypes': np.eye(3), 'logit_scale': np.array(2.), 'mean': np.zeros(3),
              'scale': np.ones(3), 'coef': np.eye(3), 'intercept': np.zeros(3)}
    metadata = {'classes': classes, 'head_classes': classes, 'prior_weight': .5, 'threshold': .8,
                'processing': processing_contract(load_config()), 'encoder_sha256': 'f' * 64}
    return head_model(arrays, metadata)


def test_regular_and_balanced_heads_are_reproducible_and_preserve_baseline():
    base = model_fixture()
    saved = deepcopy(base.arrays)
    x = np.random.default_rng(7).normal(size=(40, 3))
    y = ['glass'] * 25 + ['metal'] * 10 + ['unknown'] * 5
    for balanced in (False, True):
        first = fit_candidate(base, x, y, .1, balanced)
        second = fit_candidate(base, x, y, .1, balanced)
        for key in first.arrays:
            np.testing.assert_array_equal(first.arrays[key], second.arrays[key])
        assert np.allclose(probabilities(first, x).sum(axis=1), 1)
    for key in saved:
        np.testing.assert_array_equal(saved[key], base.arrays[key])
    assert base.metadata['head_classes'] == ['glass', 'metal', 'unknown']
    assert not np.array_equal(fit_candidate(base, x, y, .1, False).arrays['coef'],
                              fit_candidate(base, x, y, .1, True).arrays['coef'])


def test_binary_head_alignment_and_missing_training_classes():
    base = model_fixture()
    x = np.array([[0, 1, 0], [1, 0, 0], [.1, .9, 0], [.9, .1, 0]])
    model = fit_candidate(base, x, ['metal', 'glass', 'metal', 'glass'], .1, False)
    assert model.arrays['coef'].shape == (2, 3)
    assert probabilities(model, x).shape == (4, 3)
    with pytest.raises(ValueError, match='two training classes'):
        fit_candidate(base, x, ['metal'] * 4, .1, False)


def rows_fixture(n=10):
    return [{'class_id': c, 'object_id': f'{c}-{i}', 'session_id': f's-{c}-{i}'}
            for c in ('glass', 'metal', 'unknown') for i in range(n)]


def test_calibration_split_preserves_connected_objects_and_sessions():
    rows = rows_fixture(40)
    # A repeated object joins two capture sessions; both must stay together.
    rows[1]['object_id'] = rows[0]['object_id']
    cal, selected = validation_partition(rows, 5)
    assert cal and selected
    for field in ('object_id', 'session_id'):
        assert not {rows[i][field] for i in cal} & {rows[i][field] for i in selected}
    assert validation_partition(rows, 5) == (cal, selected)
    assert validation_partition(rows_fixture(1), 10) == ([], [0, 1, 2])


def test_calibration_can_abstain_without_artificial_support():
    base = model_fixture()
    rows = rows_fixture(10)
    # All-zero embeddings cannot produce reliable class-specific accepted decisions.
    rule = calibrate(base, np.zeros((len(rows), 3)), rows, 10)
    assert rule['temperature'] in (.75, 1, 1.5, 2)
    assert all(v is None for v in rule['thresholds'].values())
    metrics = evaluate_candidate(base, np.zeros((len(rows), 3)), rows, rule)
    assert metrics['accepted'] == 0 and metrics['accepted_precision'] is None
    assert metrics['top1']['total'] == len(rows)


def test_supported_calibration_uses_only_given_validation_embeddings():
    base = model_fixture()
    rows = rows_fixture(10)
    x = np.repeat(np.eye(3) * 8, 10, axis=0)
    rule = calibrate(base, x, rows, 10)
    assert rule['thresholds'] == {'glass': .5, 'metal': .5}
    calibrated = evaluate_candidate(base, x, rows, rule)
    assert calibrated['accepted_precision'] == 1
    assert calibrated['top1']['total'] == 30
    assert calibrated['coverage'] == 2 / 3  # Unknown still abstains.


def test_metrics_include_severe_confusions_and_gate_rejects_regressions():
    base = model_fixture()
    rows = rows_fixture(10)
    rule = {'temperature': 1., 'thresholds': {'glass': 0., 'metal': 0.}}
    metrics = evaluate_candidate(base, np.tile([1., 0., 0.], (len(rows), 1)), rows, rule)
    assert metrics['coverage'] == 1
    assert metrics['wrong_accepted'] == 20
    assert metrics['severe_confusions']['out_of_scope_accepted'] == 10
    assert metrics['top1']['confusion_matrix'][2][0] == 10
    reference = evaluate_candidate(base, np.repeat(np.eye(3) * 8, 10, axis=0), rows, rule)
    reference['top1']['macro_f1'] = .5
    candidate = deepcopy(reference)
    candidate['top1']['macro_f1'] = .51
    assert gate(candidate, reference, experiment.DEFAULT_POLICY) == []
    for key, value, reason in [('coverage', .4, 'coverage_regression'),
                              ('accepted_precision', .94, 'accepted_precision_regression_or_insufficient'),
                              ('wrong_accepted', 1, 'more_confident_errors'),
                              ('head_ms_per_image', 10000, 'head_latency_regression')]:
        changed = deepcopy(candidate)
        changed[key] = value
        assert reason in gate(changed, reference, experiment.DEFAULT_POLICY)
    changed = deepcopy(candidate)
    changed['top1']['by_class']['glass']['recall'] = 0
    assert 'recall_regression:glass' in gate(changed, reference, experiment.DEFAULT_POLICY)
    changed = deepcopy(candidate)
    changed['support']['glass']['objects'] = 1
    assert 'insufficient_support:glass' in gate(changed, reference, experiment.DEFAULT_POLICY)
    changed = deepcopy(candidate)
    changed['severe_confusions']['out_of_scope_accepted'] += 1
    assert 'severe_confusion_regression' in gate(changed, reference, experiment.DEFAULT_POLICY)
    changed = deepcopy(candidate)
    changed['accepted_by_class']['glass']['precision'] = .94
    assert 'accepted_precision_regression:glass' in gate(changed, reference, experiment.DEFAULT_POLICY)


@pytest.fixture
def local_inputs(tmp_path):
    config = replace(load_config(), directories={**load_config().directories, 'models': tmp_path / 'models'})
    folder = config.directories['models'] / 'semantic-v1'
    folder.mkdir(parents=True)
    model = model_fixture()
    (folder / 'semantic.json').write_text(json.dumps(model.metadata))
    np.savez(folder / 'head.npz', **model.arrays)
    (folder / 'LICENSE-CLIP').write_text('Synthetic model fixture, not a field artifact')
    (folder / 'learning_seed.json').write_text(json.dumps({'training_hashes': [], 'validation_hashes': []}))
    source = tmp_path / 'photos'
    source.mkdir()
    rows = []
    for split in ('train', 'validation', 'test'):
        for index, label in enumerate(model.classes):
            path = source / f'{split}-{label}.png'
            pixels = np.random.default_rng(len(rows)).integers(0, 255, (64, 64, 3), dtype=np.uint8)
            Image.fromarray(pixels).save(path)
            rows.append({'path': path.name, 'class_id': label, 'split': split,
                         'object_id': f'obj-{len(rows)}', 'session_id': f's-{len(rows)}',
                         'sha256': file_digest(path), 'rgb_sha256': array_digest(pixels),
                         'license': 'private-consent', 'consent': True, 'source_kind': 'synthetic_fixture'})
    manifest, audit, policy = tmp_path / 'manifest.json', tmp_path / 'audit.json', tmp_path / 'policy.json'
    manifest.write_text(json.dumps(rows))
    policy.write_text(json.dumps(experiment.DEFAULT_POLICY))
    receipt = {'manifest_sha256': file_digest(manifest), 'policy_sha256': file_digest(policy),
               'audit_status': 'approved', 'scope': 'offline_training_and_evaluation',
               'reviewer_id': 'fixture-auditor', 'evidence_reference': 'fixture-only',
               'reviewed_at': '2026-11-07T12:00:00-03:00', 'development_overlap_reviewed': True,
               'approved_augmentations': list(AUGMENTATIONS)}
    audit.write_text(json.dumps(receipt))
    return config, source, rows, manifest, audit, policy, model, receipt


def test_public_gate_refuses_synthetic_photos_and_unbound_audits(local_inputs):
    _, _, rows, manifest, audit, policy, model, receipt = local_inputs
    with pytest.raises(ValueError, match='field photos'):
        audit_inputs(manifest, audit, policy, model.classes)
    receipt['manifest_sha256'] = '0' * 64
    audit.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='exact manifest'):
        audit_inputs(manifest, audit, policy, model.classes)
    cli = importlib.import_module('scripts.experiment_semantic_candidates')
    with pytest.raises(SystemExit) as error:
        cli.main(['fit', '--manifest', str(manifest), '--audit', str(audit), '--policy', str(policy),
                  '--source', str(manifest.parent), '--run', 'technical'])
    assert error.value.code == 2
    assert not (local_inputs[0].directories['models'] / 'candidates').exists()


def test_cache_key_integrity_and_training_only_augmentations(local_inputs, tmp_path):
    config, source, rows, _, _, _, model, _ = local_inputs
    model.image_features = Mock(side_effect=lambda rgb: rgb.astype(np.float32).mean(axis=(0, 1)) / 255)
    cache = EmbeddingCache(tmp_path / 'cache', model, config)
    row = rows[0]
    first = cache.feature(source, row)
    np.testing.assert_array_equal(first, cache.feature(source, row))
    assert model.image_features.call_count == 1
    for component in ('encoder', 'processing', 'code'):
        original = cache.identity[component]
        cache.identity[component] = 'different-' + component
        cache.feature(source, row)
        cache.identity[component] = original
    assert model.image_features.call_count == 4
    assert not np.array_equal(first, cache.feature(source, row, 'brightness-0.9'))
    assert file_digest(source / row['path']) == row['sha256']
    with pytest.raises(ValueError, match='training'):
        cache.feature(source, rows[-1], 'brightness-1.1')
    for path in (tmp_path / 'cache').glob('*.npy'):
        path.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='Corrupt'):
        cache.feature(source, row)


@pytest.fixture
def technical_runner(local_inputs, monkeypatch):
    config, source, rows, manifest, audit, policy, model, receipt = local_inputs
    # Test-only injection isolates the external provenance gate. CLI has no bypass flag.
    monkeypatch.setattr(experiment, 'audit_inputs', lambda *args: (rows, receipt))
    model.image_features = Mock(side_effect=lambda rgb: rgb.astype(np.float32).mean(axis=(0, 1)) / 255)
    monkeypatch.setattr(experiment, 'SemanticOnnxClassifier', lambda *args: model)
    monkeypatch.setattr(experiment, 'REGULARIZATION', (.1,))
    return local_inputs


def test_fit_is_reproducible_and_never_opens_test_images(technical_runner):
    config, source, rows, manifest, audit, policy, model, _ = technical_runner
    for row in rows:
        if row['split'] == 'test':
            (source / row['path']).unlink()  # Fit must succeed without opening final photos.
    first = experiment.fit_experiment(config, manifest, audit, policy, source, 'run-a')
    second = experiment.fit_experiment(config, manifest, audit, policy, source, 'run-b')
    assert first['decision'] == second['decision'] == 'NO-GO'
    assert not first['test_opened']
    a = json.loads((config.directories['models'] / 'candidates/run-a/freeze.json').read_text())
    b = json.loads((config.directories['models'] / 'candidates/run-b/freeze.json').read_text())
    assert a['models'] == b['models']
    assert a['identity'] == b['identity']
    assert first['calibration'] == 'not_run_insufficient_group_support'
    with pytest.raises(ValueError, match='NO-GO'):
        experiment.final_test(config, manifest, audit, policy, source, 'run-a')
    assert not (config.directories['models'] / 'candidates/test-ledger').exists()


def test_known_historical_test_images_block_before_any_fit(technical_runner):
    config, source, rows, manifest, audit, policy, model, _ = technical_runner
    (config.directories['models'] / 'semantic-v1/learning_seed.json').write_text(
        json.dumps({'training_hashes': [rows[-1]['sha256']]}))
    with pytest.raises(ValueError, match='historical'):
        experiment.fit_experiment(config, manifest, audit, policy, source, 'blocked')
    model.image_features.assert_not_called()
    assert not (config.directories['models'] / 'candidates').exists()


def test_single_final_test_is_reserved_before_any_test_open(technical_runner, monkeypatch):
    config, source, rows, manifest, audit, policy, model, _ = technical_runner
    monkeypatch.setattr(experiment, 'gate', lambda *args: [])  # Test the state machine, not a gain claim.
    experiment.fit_experiment(config, manifest, audit, policy, source, 'frozen')
    result = experiment.final_test(config, manifest, audit, policy, source, 'frozen')
    assert result['published'] is False and result['independent_test'] is False
    assert result['test_original_images'] == 3  # No augmented views counted as test support.
    calls = model.image_features.call_count
    with pytest.raises(FileExistsError):
        experiment.final_test(config, manifest, audit, policy, source, 'frozen')
    assert model.image_features.call_count == calls
    # Another run cannot reuse the same holdout just by changing output name.
    experiment.fit_experiment(config, manifest, audit, policy, source, 'other')
    with pytest.raises(FileExistsError):
        experiment.final_test(config, manifest, audit, policy, source, 'other')
    # A partly overlapping holdout also cannot reuse already-tested RGB content.
    row = rows[-1]
    path = source / 'new-test.png'
    pixels = np.full((64, 64, 3), (100, 150, 200), dtype=np.uint8)
    Image.fromarray(pixels).save(path)
    row.update(path=path.name, sha256=file_digest(path), rgb_sha256=array_digest(pixels))
    manifest.write_text(json.dumps(rows))
    experiment.fit_experiment(config, manifest, audit, policy, source, 'overlap')
    calls = model.image_features.call_count
    with pytest.raises(FileExistsError):
        experiment.final_test(config, manifest, audit, policy, source, 'overlap')
    assert model.image_features.call_count == calls


def test_tampering_and_failed_final_test_consume_no_retuning_opportunity(technical_runner, monkeypatch):
    config, source, rows, manifest, audit, policy, _, _ = technical_runner
    monkeypatch.setattr(experiment, 'gate', lambda *args: [])
    experiment.fit_experiment(config, manifest, audit, policy, source, 'frozen')
    row = rows[-1]
    (source / row['path']).write_bytes(b'invalid')
    with pytest.raises(ValueError):
        experiment.final_test(config, manifest, audit, policy, source, 'frozen')
    with pytest.raises(FileExistsError):
        experiment.final_test(config, manifest, audit, policy, source, 'frozen')


def test_frozen_artifact_and_policy_checksums_are_enforced(technical_runner, monkeypatch):
    config, source, _, manifest, audit, policy, _, _ = technical_runner
    monkeypatch.setattr(experiment, 'gate', lambda *args: [])
    experiment.fit_experiment(config, manifest, audit, policy, source, 'frozen')
    folder = config.directories['models'] / 'candidates/frozen'
    frozen = json.loads((folder / 'freeze.json').read_text())
    (folder / frozen['models'][frozen['selected']]['weights_file']).write_bytes(b'tampered')
    with pytest.raises(ValueError, match='checksum'):
        experiment.final_test(config, manifest, audit, policy, source, 'frozen')
    assert not (config.directories['models'] / 'candidates/test-ledger').exists()
    policy.write_text('{}')
    with pytest.raises(ValueError, match='changed'):
        experiment.final_test(config, manifest, audit, policy, source, 'frozen')
