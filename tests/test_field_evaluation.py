"""Hand-computed scores on synthetic fixtures; these are not field benchmarks."""
import csv
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ecoscan.classification.prediction import ClassificationPrediction
from ecoscan.config import load_config
from ecoscan.services import field_evaluation as field
from tests.test_field_manifest_cli import collection as collection, build


@pytest.fixture
def inputs(collection, tmp_path, monkeypatch):
    source, rows, _ = collection
    for row in rows:
        row['split'] = 'test'
    rows[0]['scenario'] = 'transparent_plastic'
    rows[1]['scenario'] = 'transparent_glass'
    rows[2]['scenario'] = 'reflective_metal'
    records = build(collection)
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps(records))
    model = tmp_path / 'semantic.json'
    metadata = json.loads(Path('models/semantic-v1/semantic.json').read_text())
    model.write_text(json.dumps(metadata))
    labels = ['glass', 'glass', 'metal', 'plastic']
    scores = [.95, .85, .7, .99]
    predictions = [ClassificationPrediction(label, label if score >= .8 else None, score,
                                            {label: score}, score >= .8, .8)
                   for label, score in zip(labels, scores, strict=True)]
    predict = Mock(side_effect=predictions)
    constructor = Mock(return_value=SimpleNamespace(metadata=metadata, predict_image=predict))
    monkeypatch.setattr(field, 'SemanticOnnxClassifier', constructor)
    return source, manifest, model, records, predict, constructor


def evaluate(inputs):
    source, manifest, model, *_ = inputs
    return field.evaluate_field_manifest(load_config(), model, manifest, source)


def test_metrics_precede_confirmation_and_include_out_of_scope_false_positives(inputs, tmp_path):
    report = evaluate(inputs)
    assert report['source_kind'] == 'synthetic_fixture'
    assert report['independent_test'] is False
    assert report['top1']['accuracy'] == .5
    assert report['top1']['macro_f1'] == pytest.approx(5 / 12)
    assert report['top1']['by_class']['glass']['precision'] == .5
    assert report['top1']['by_class']['metal']['recall'] == 1
    assert report['accepted']['accuracy'] == .25  # Denominator is all images, not only accepted ones.
    assert report['acceptance'] == {'threshold': .8, 'accepted': 3, 'correct': 1, 'wrong': 2,
                                    'rejected': 1, 'coverage': .75, 'selective_error_rate': 2 / 3}
    assert report['counts']['glass']['false_positives_top1'] == 1
    assert report['counts']['plastic']['false_positives_accepted'] == 1
    assert report['counts']['plastic']['false_positive_rate_accepted'] == pytest.approx(1 / 3)
    assert report['counts']['metal']['objects'] == 1
    assert report['counts']['metal']['rejected'] == 1
    assert sum(map(sum, report['top1']['confusion_matrix'])) == 4
    assert report['scenarios']['transparent_plastic']['top1']['accuracy'] == 0
    assert report['scenarios']['standard']['images'] == 0
    assert report['scenarios']['standard']['top1'] is None
    curve = {r['threshold']: r for r in report['selectivity']}
    assert curve[0]['coverage'] == 1
    assert curve[.9]['selective_error_rate'] == 1
    assert curve[1]['selective_error_rate'] is None
    for data in report['latency_ms'].values():
        assert 0 <= data['min'] <= data['p50'] <= data['p95'] <= data['max']
    inputs[-2].assert_called()
    assert inputs[-2].call_count == 4
    assert all(call.args[0].shape == (224, 224, 3) for call in inputs[-2].call_args_list)
    output = tmp_path / 'reports' / 'evaluation.json'
    field.write_field_report(report, output)
    assert all(p.exists() for p in field.report_paths(output).values())
    assert 'object_id' not in output.read_text()
    assert str(inputs[0]) not in output.read_text()
    assert 'fixture-0.png' not in output.read_text()
    with output.with_suffix('.summary.csv').open() as file:
        summary = {r['metric']: r['value'] for r in csv.DictReader(file)}
    assert float(summary['macro_f1']) == pytest.approx(5 / 12)
    assert summary['independent_test'] == 'False'
    assert summary['model_metadata_sha256'] == report['integrity']['model_metadata_sha256']
    with output.with_suffix('.csv').open() as file:
        classes = {r['class_id']: r for r in csv.DictReader(file)}
    assert classes['plastic']['false_positives_accepted'] == '1'
    assert 'independent_test=false' in output.with_suffix('.md').read_text()
    with pytest.raises(ValueError, match='new report'):
        field.write_field_report(report, output)


@pytest.mark.parametrize('mutation', ['hash', 'consent', 'leak', 'config', 'symlink'])
def test_invalid_input_fails_before_loading_encoder(inputs, mutation, tmp_path):
    source, manifest, model, records, _, constructor = inputs
    if mutation == 'hash':
        records[0]['sha256'] = 'a' * 64
    elif mutation == 'consent':
        records[0]['consent'] = False
    elif mutation == 'leak':
        records[0]['split'] = 'train'
        records[-1]['session_id'] = records[0]['session_id']
    elif mutation == 'config':
        metadata = json.loads(model.read_text())
        metadata['processing']['profile']['padding_rgb'] = 0
        model.write_text(json.dumps(metadata))
    else:
        path = source / records[0]['path']
        outside = tmp_path / 'outside.png'
        path.rename(outside)
        path.symlink_to(outside)
    manifest.write_text(json.dumps(records))
    with pytest.raises(ValueError):
        evaluate(inputs)
    constructor.assert_not_called()


def test_only_test_split_is_inferred_but_all_splits_are_verified(inputs):
    source, manifest, _, records, predict, _ = inputs
    records[1]['split'] = 'validation'
    manifest.write_text(json.dumps(records))
    report = evaluate(inputs)
    assert report['top1']['total'] == 3
    assert predict.call_count == 3
    predict.reset_mock()
    # Training/validation entries cannot hide non-local or changed photos.
    (source / records[1]['path']).write_bytes(b'corrupt')
    with pytest.raises(ValueError):
        evaluate(inputs)
    predict.assert_not_called()


def test_regression_cases_are_only_frozen_subset(inputs, tmp_path):
    source, manifest, model, records, _, _ = inputs
    cases = tmp_path / 'cases.csv'
    cases.write_text(f"path,expected_class\n{records[0]['path']},plastic\n")
    report = field.evaluate_field_manifest(load_config(), model, manifest, source, cases_path=cases)
    assert len(report['cases']) == 1
    assert report['cases'][0]['record_index'] == 0
    assert report['integrity']['cases_sha256']
    cases.write_text('path,expected_class\n../outside.png,plastic\n')
    inputs[-1].reset_mock()
    with pytest.raises(ValueError, match='frozen test'):
        field.evaluate_field_manifest(load_config(), model, manifest, source, cases_path=cases)
    inputs[-1].assert_not_called()


def test_cli_generates_all_formats_and_refuses_existing_sidecar(inputs, tmp_path):
    cli = importlib.import_module('scripts.validate_semantic_onnx')
    source, manifest, model, *_ = inputs
    output = tmp_path / 'report.json'
    argv = ['--model', str(model), '--source', str(source), '--manifest', str(manifest), '--output', str(output)]
    assert cli.main(argv) == 0
    assert len(list(tmp_path.glob('report*'))) == len(field.report_paths(output))
    inputs[-1].reset_mock()
    fresh = tmp_path / 'existing.json'
    fresh.with_suffix('.md').write_text('keep')
    with pytest.raises(SystemExit) as error:
        cli.main([*argv[:-1], str(fresh)])
    assert error.value.code == 2
    assert not fresh.exists()
    assert fresh.with_suffix('.md').read_text() == 'keep'
    inputs[-1].assert_not_called()


def test_all_rejected_decisions_have_no_measured_selective_error():
    row = {'expected': 'unknown', 'object_id': 'o', 'session_id': 's', 'scenario': 'out_of_scope',
           'top_class_id': 'unknown', 'score': .99, 'accepted_class': None,
           'pipeline_ms': 0, 'inference_ms': 0, 'total_ms': 0}
    report = field.summarize_predictions([row], ['metal', 'unknown'], .8)
    assert report['top1']['accuracy'] == 1
    assert report['acceptance']['coverage'] == 0
    assert all(r['selective_error_rate'] is None for r in report['selectivity'])
    assert all(r['accepted'] == 0 for r in report['selectivity'])


def test_zero_images_never_produces_metrics():
    with pytest.raises(ValueError, match='No test predictions'):
        field.summarize_predictions([], ['metal'], .8)
