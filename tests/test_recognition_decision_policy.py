"""Synthetic proof documents test gate validation, not real independent performance."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from PIL import Image
import pytest

from ecoscan.classification.prediction import ClassificationPrediction
from ecoscan.classification.runtime import ModelLoadError
from ecoscan.config import load_config
from ecoscan.image_processing.contracts import processing_contract
from ecoscan.image_processing.validation import ImageValidationError
from ecoscan.services.recognition_policy import ENGINE_VERSION, LABELS, decision_code_sha256, load_decision_policy
from ecoscan.services.recognition_safety import (
    RecognitionInput, build_recognition_safety_decision, decide_recognition, decision_for_result,
    decision_from_error, decision_metrics_snapshot, record_decision,
)


BINDING = dict(zip(('model_metadata_sha256', 'encoder_sha256', 'head_sha256', 'processing_sha256'),
                   (c * 64 for c in 'abcd'), strict=True))


def scores(label='metal', value=.9, competitor='glass'):
    result = {c: 0.0 for c in [*LABELS, 'unknown']}
    result[label] = value
    result[competitor if competitor != label else 'metal'] = 1 - value
    return result


def input_for(label='metal', value=.9):
    return RecognitionInput(top_class=label, probabilities=scores(label, value), probability=value,
                            artifact_accepted=True, artifact_threshold=.8, capture_status='good',
                            model_sha256=BINDING['model_metadata_sha256'], encoder_sha256=BINDING['encoder_sha256'],
                            head_sha256=BINDING['head_sha256'], processing_sha256=BINDING['processing_sha256'])


class EvidenceFixture:
    """All files stay under pytest tmp_path; none represent a real audit or photos."""
    def __init__(self, tmp_path, label='metal'):
        self.config = replace(load_config(), project_root=tmp_path)
        self.label = label
        self.folder = tmp_path / 'reports/recognition_evidence'
        self.folder.mkdir(parents=True)
        self.policy = json.loads(Path('config/recognition_policy.json').read_text())
        self.policy['classes'][label].update(assertive=True, threshold=.85, min_margin=.2, max_unknown_score=.05)
        self.audit = {'approved': True, 'independence_reviewed': True, 'object_session_splits_reviewed': True,
                      'consent_reviewed': True, 'decision_rule_reviewed': True,
                      'evaluation_manifest_sha256': 'e' * 64, 'reviewer_id': 'fixture-reviewer'}
        self.audit['calibration_manifest_sha256'] = 'f' * 64
        self.calibration = {'class_id': label, 'method': 'temperature_scaling', 'split': 'validation', 'held_out': True,
                            'manifest_sha256': 'f' * 64, 'integrity': BINDING.copy(), 'threshold': .85,
                            'min_margin': .2, 'max_unknown_score': .05, 'objects': 30, 'sessions': 3,
                            'ece': .05, 'temperature': 1.0}
        self.evaluation = {'source_kind': 'field_photo', 'independent_test': False,
                           'integrity': {**BINDING, 'manifest_sha256': 'e' * 64},
                           'counts': {label: {'objects': 30, 'sessions': 3}, 'unknown': {'objects': 10}},
                           'accepted': {'by_class': {label: {'precision': .97}}},
                           'top1': {'by_class': {label: {'recall': .9}}},
                           'decision_evaluation': {label: {'reference_objects': 30, 'identified_objects': 30,
                               'correct_objects': 30, 'threshold': .85, 'min_margin': .2,
                               'max_unknown_score': .05, 'temperature': 1.0}}}
        self.gate = {'schema_version': 1, 'class_id': label, 'approved': True, 'approval_reference': 'fixture-approval',
                     'engine_version': ENGINE_VERSION, 'engine_sha256': decision_code_sha256(), 'policy_version': self.policy['version']}
        self.evaluation['decision_evaluation'][label].update(engine_sha256=decision_code_sha256(), policy_version=self.policy['version'])
        self.save()

    def document(self, name, value):
        path = self.folder / (name + '.json')
        path.write_text(json.dumps(value))
        return {'path': path.relative_to(self.config.project_root).as_posix(),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    def save(self):
        self.gate['calibration'] = self.document('calibration', self.calibration)
        self.evaluation['decision_evaluation'][self.label]['calibration_sha256'] = self.gate['calibration']['sha256']
        self.gate['evaluation'] = self.document('evaluation', self.evaluation)
        self.gate['source_audit'] = self.document('audit', self.audit)
        self.policy['classes'][self.label]['evidence'] = self.document('gate', self.gate)
        path = self.config.project_root / 'config/recognition_policy.json'
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(self.policy))

    def decide(self, data=None):
        return decide_recognition(data or input_for(self.label), load_decision_policy(self.config))


@pytest.fixture
def proof(tmp_path):
    return EvidenceFixture(tmp_path)


def test_all_deployed_classes_are_opt_in_disabled_and_global_confirmation_stays_true():
    config = load_config()
    assert config.model['confirmation_required'] is True
    assert all(not p.assertive for p in load_decision_policy(config).classes.values())
    for label in LABELS:
        decision = decide_recognition(input_for(label), load_decision_policy(config))
        assert decision.status == 'probable'
        assert decision.title.startswith('Melhor correspondência: ')
        assert not decision.allow_disposal_guidance
        assert decision.requires_confirmation and decision.can_correct


def test_complete_hash_bound_independent_gate_allows_categorical_communication_only(proof):
    decision = proof.decide()
    assert decision.status == 'identified'
    assert decision.title == 'Material identificado: METAL'
    assert decision.decision_reason == ('independent_gate_passed',)
    assert len(decision.evidence_sha256) == 64
    assert not decision.allow_disposal_guidance
    assert decision.can_correct and decision.requires_confirmation


@pytest.mark.parametrize('mutation', ['unapproved', 'no_external_audit', 'no_rule_review', 'synthetic', 'flipped_independent_flag',
    'low_objects', 'nonfinite_support', 'low_sessions', 'no_negatives', 'poor_precision', 'poor_recall',
    'same_test_for_calibration', 'uncalibrated', 'high_ece', 'mismatched_rule', 'no_identified_support', 'bad_decision_precision',
    'calibration_artifact_mismatch', 'engine_code_mismatch'])
def test_incomplete_or_wrong_proof_cannot_identify(proof, mutation):
    if mutation == 'unapproved':
        proof.gate['approved'] = False
    elif mutation == 'no_external_audit':
        proof.audit['independence_reviewed'] = False
    elif mutation == 'no_rule_review':
        proof.audit['decision_rule_reviewed'] = False
    elif mutation == 'synthetic':
        proof.evaluation['source_kind'] = 'synthetic_fixture'
    elif mutation == 'flipped_independent_flag':
        proof.evaluation['independent_test'] = True
    elif mutation == 'low_objects':
        proof.evaluation['counts']['metal']['objects'] = 29
    elif mutation == 'nonfinite_support':
        proof.evaluation['counts']['metal']['objects'] = float('nan')
    elif mutation == 'low_sessions':
        proof.evaluation['counts']['metal']['sessions'] = 2
    elif mutation == 'no_negatives':
        proof.evaluation['counts']['unknown']['objects'] = 0
    elif mutation == 'poor_precision':
        proof.evaluation['accepted']['by_class']['metal']['precision'] = .94
    elif mutation == 'poor_recall':
        proof.evaluation['top1']['by_class']['metal']['recall'] = .79
    elif mutation == 'same_test_for_calibration':
        proof.calibration['manifest_sha256'] = 'e' * 64
    elif mutation == 'uncalibrated':
        proof.calibration['held_out'] = False
    elif mutation == 'high_ece':
        proof.calibration['ece'] = .11
    elif mutation == 'mismatched_rule':
        proof.evaluation['decision_evaluation']['metal']['min_margin'] = .01
    elif mutation == 'no_identified_support':
        proof.evaluation['decision_evaluation']['metal']['identified_objects'] = 0
    elif mutation == 'bad_decision_precision':
        proof.evaluation['decision_evaluation']['metal']['correct_objects'] = 28
    elif mutation == 'calibration_artifact_mismatch':
        proof.calibration['integrity']['head_sha256'] = '0' * 64
    elif mutation == 'engine_code_mismatch':
        proof.gate['engine_sha256'] = '0' * 64
    proof.save()  # Rebind file hashes, so this tests schema/evidence checks, not just a bad checksum.
    decision = proof.decide()
    assert decision.status == 'probable'
    assert not decision.title.startswith('Material identificado')


@pytest.mark.parametrize('field', ['model_sha256', 'encoder_sha256', 'head_sha256', 'processing_sha256'])
def test_opt_in_is_bound_to_exact_runtime_artifacts(proof, field):
    decision = proof.decide(replace(input_for(), **{field: '0' * 64}))
    assert decision.status == 'probable'
    assert 'evidence_artifact_mismatch' in decision.decision_reason


@pytest.mark.parametrize(('change', 'expected'), [({'capture_status': 'retake'}, 'retake'),
    ({'capture_status': 'attention'}, 'probable'), ({'capture_status': 'unknown'}, 'probable'),
    ({'processing_compatible': False}, 'model_unavailable'), ({'model_available': False}, 'model_unavailable'),
    ({'outside_scope': True}, 'out_of_scope'), ({'artifact_accepted': False}, 'probable')])
def test_runtime_safety_precedes_categorical_messages(proof, change, expected):
    decision = proof.decide(replace(input_for(), **change))
    assert decision.status == expected
    assert decision.can_correct and not decision.allow_disposal_guidance


@pytest.mark.parametrize(('score', 'expected'), [(.849, 'probable'), (.85, 'identified'), (.851, 'identified')])
def test_calibrated_threshold_boundary(proof, score, expected):
    assert proof.decide(input_for(value=score)).status == expected


def test_margin_unknown_competitor_and_raw_artifact_gate(proof):
    proof.policy['classes']['metal']['min_margin'] = .81
    proof.calibration['min_margin'] = proof.evaluation['decision_evaluation']['metal']['min_margin'] = .81
    proof.save()
    assert 'low_top_two_margin' in proof.decide().decision_reason
    proof.policy['classes']['metal']['min_margin'] = .2
    proof.calibration['min_margin'] = proof.evaluation['decision_evaluation']['metal']['min_margin'] = .2
    proof.save()
    assert 'unknown_competitor' in proof.decide(replace(input_for(), probabilities=scores(competitor='unknown'))).decision_reason
    assert 'artifact_rejected' in proof.decide(replace(input_for(), artifact_threshold=.95)).decision_reason


def test_temperature_is_applied_and_not_treated_as_certainty(proof):
    proof.calibration['temperature'] = proof.evaluation['decision_evaluation']['metal']['temperature'] = 2.
    proof.save()
    assert 'below_calibrated_threshold' in proof.decide().decision_reason


@pytest.mark.parametrize('bad', [None, True, float('nan'), float('inf'), -1., 1.1, '.99', 10 ** 1000])
def test_invalid_scores_fail_closed(proof, bad):
    data = input_for()
    vector = {**data.probabilities, 'metal': bad}
    assert proof.decide(replace(data, probabilities=vector, probability=bad)).status == 'unrecognized'


def test_ties_missing_vector_or_wrong_argmax_do_not_create_a_material_claim(proof):
    for vector in ({}, {'metal': 1.}, scores(value=.5), scores('glass', .9)):
        decision = proof.decide(replace(input_for(), probabilities=vector, probability=vector.get('metal')))
        assert decision.status == 'unrecognized'
        assert decision.suggested_class is None
    assert proof.decide(replace(input_for(), top_class='unknown')).status == 'out_of_scope'


@pytest.mark.parametrize('label', ['plastic', 'glass', 'battery', 'electronic'])
def test_transparency_and_special_collection_do_not_bypass_policy(tmp_path, label):
    proof = EvidenceFixture(tmp_path, label)
    if label in ('battery', 'electronic'):
        decision = proof.decide()
        assert decision.status == 'probable'
        assert 'Coleta especial' in decision.message
    else:
        disabled = load_decision_policy(load_config())
        decision = decide_recognition(input_for(label), disabled)
        assert decision.title == 'Melhor correspondência: ' + LABELS[label]
    assert 'não confirma composição' in decision.message
    assert decision.requires_confirmation and decision.can_correct


def test_cached_result_cannot_keep_revoked_policy_and_wrong_high_score_remains_correctable(proof):
    data = input_for()
    result = SimpleNamespace(**data.__dict__, pipeline=SimpleNamespace(metadata={
        'capture_quality': {'status': 'good'}, 'quality': {'before_filter': {'exposure_status': 'ok', 'focus_status': 'ok'}},
        'recognition_preparation': {'contract': {'sha256': data.processing_sha256}}}),
        accepted=False, expected_class='glass')  # Ground truth is NOT available to the decision engine.
    assert decision_for_result(result, proof.config).status == 'identified'
    proof.audit['approved'] = False
    proof.save()
    decision = decision_for_result(result, proof.config)
    assert decision.status == 'probable' and decision.can_correct
    assert not decision.allow_disposal_guidance


@pytest.mark.parametrize(('field', 'value'), [('exposure_status', 'underexposed'), ('focus_status', 'low')])
def test_original_dark_or_blurred_capture_cannot_be_overridden_by_capture_flag(proof, field, value):
    data = input_for()
    result = SimpleNamespace(**data.__dict__, pipeline=SimpleNamespace(metadata={
        'capture_quality': {'status': 'good'}, 'quality': {'before_filter': {field: value}}}))
    assert build_recognition_safety_decision(result).status == 'retake'


def test_missing_invalid_policy_or_evidence_path_never_enables_assertiveness(proof):
    path = proof.config.project_root / 'config/recognition_policy.json'
    for contents in ('invalid', 'null', '[]', '{}'):
        path.write_text(contents)
        assert proof.decide().status == 'probable'
    proof.save()
    proof.policy['classes']['metal']['evidence']['path'] = '/outside/gate.json'
    path.write_text(json.dumps(proof.policy))
    assert proof.decide().status == 'probable'
    path.unlink()
    assert proof.decide().status == 'probable'


def test_private_logs_and_metrics_do_not_contain_paths_images_or_accounts(caplog):
    before = decision_metrics_snapshot().get('total', 0)
    decision = decide_recognition(input_for())
    with caplog.at_level('INFO'):
        record_decision(decision)
    assert 'decision_reason=' in caplog.text and 'policy_version=' in caplog.text
    assert 'private-upload' not in caplog.text and 'supabase_' not in caplog.text
    assert decision_metrics_snapshot()['total'] == before + 1
    assert 0 <= decision_metrics_snapshot()['rejection_rate'] <= 1
    for error in (ImageValidationError('/private-upload.png'), ModelLoadError('/private-model.json')):
        failure = decision_from_error(error)
        assert failure.can_correct and not failure.allow_disposal_guidance
        assert 'private-' not in str(failure)


def test_analysis_preserves_raw_acceptance_without_disabling_confirmation(tmp_path):
    from ecoscan.services.analysis_service import analyze_waste_image
    config = load_config()
    path = tmp_path / 'synthetic.png'
    Image.fromarray(np.random.default_rng(1).integers(0, 255, (64, 64, 3), dtype=np.uint8)).save(path)
    metadata = json.loads(Path('models/semantic-v1/semantic.json').read_text())
    bundle = SimpleNamespace(model_type='semantic_onnx_assisted', classifier=SimpleNamespace(metadata=metadata))
    prediction = ClassificationPrediction('metal', 'metal', .9, scores(), True, .8)
    with patch('ecoscan.services.analysis_service._predict', return_value=prediction):
        result = analyze_waste_image(path, config, model_bundle=bundle)
    assert result.artifact_accepted is True
    assert result.artifact_threshold == .8
    assert result.accepted is False and result.predicted_class is None
    assert result.decision.status == 'probable'
    assert result.decision.title == 'Melhor correspondência: METAL'
    assert result.pipeline.metadata['recognition_preparation']['contract'] == processing_contract(config)
    incompatible = deepcopy(bundle)
    incompatible.classifier.metadata['processing'] = {}
    with patch('ecoscan.services.analysis_service._predict', return_value=prediction):
        assert analyze_waste_image(path, config, model_bundle=incompatible).decision.status == 'model_unavailable'


def test_opt_in_boolean_or_incomplete_evidence_cannot_create_categorical_output(proof):
    for evidence in (None, {}, {'path': 'reports/recognition_evidence/missing.json', 'sha256': 'a' * 64}):
        proof.policy['classes']['metal']['evidence'] = evidence
        path = proof.config.project_root / 'config/recognition_policy.json'
        path.write_text(json.dumps(proof.policy))
        assert proof.decide().status == 'probable'


def test_ui_error_logging_does_not_expose_private_detail(caplog):
    from unittest.mock import Mock
    from ecoscan.ui.common_views import _render_user_error
    st = SimpleNamespace(error=Mock(), info=Mock())
    with caplog.at_level('WARNING'):
        _render_user_error(st, ModelLoadError('/private-upload/person@example.com'), context='image_analysis')
    assert 'MODEL-001' in caplog.text
    assert '/private-upload' not in caplog.text and 'person@example.com' not in caplog.text
    assert 'person@example.com' not in str(st.error.call_args)


def test_invalid_local_file_and_model_failure_record_rejection_without_private_paths(tmp_path, caplog):
    from ecoscan.services.analysis_service import analyze_waste_image
    config = load_config()
    image = tmp_path / 'synthetic.png'
    image.write_bytes(b'invalid')
    with pytest.raises(ImageValidationError):
        analyze_waste_image(image, config)
    Image.fromarray(np.random.default_rng(2).integers(0, 255, (64, 64, 3), dtype=np.uint8)).save(image)
    with patch('ecoscan.services.analysis_service.load_recognition_model', side_effect=ModelLoadError('private-model-path')):
        with pytest.raises(ModelLoadError):
            analyze_waste_image(image, config)
    assert 'private-model-path' not in caplog.text
