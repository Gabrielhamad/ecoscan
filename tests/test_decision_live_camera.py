"""Live-camera presentation consumes the decision service; no score-to-label rules."""
from types import SimpleNamespace
from unittest.mock import Mock

from PIL import Image
import pytest

from ecoscan.classification.runtime import ModelLoadError
from ecoscan.config import load_config
from ecoscan.image_processing.validation import ImageValidationError
from ecoscan.live_camera import analyzer as module
from ecoscan.live_camera.server import LIVE_CAMERA_HTML
from tests.test_live_camera import _fake_decision, _fake_pipeline, _image_bytes, FakeBundle


def _result(decision=None):
    return SimpleNamespace(pipeline=_fake_pipeline(), top_class="metal", predicted_class="metal",
                           accepted=True, probability=.99, probabilities={"metal": .99},
                           message="Categoria identificada: METAL.", guidance=object(),
                           model_type="semantic_onnx_assisted", decision=decision)


def test_raw_accepted_prediction_cannot_create_live_categorical_message(monkeypatch):
    decision = _fake_decision()
    decide = Mock(return_value=decision)
    monkeypatch.setattr(module, 'decision_for_result', decide)
    monkeypatch.setattr(module, 'analyze_waste_image', lambda *args, **kwargs: _result())
    analyzer = module.LiveCameraAnalyzer(load_config(), model_bundle=FakeBundle())
    payload = analyzer.analyze_frame(_image_bytes(Image.new('RGB', (64, 64))))
    decide.assert_called_once()
    assert payload['decision']['title'] == 'Melhor correspondência: METAL'
    assert payload['message'] == decision.message
    assert not payload['accepted']
    assert payload['predicted_class'] is None
    assert payload['disposal_target'] is None
    assert payload['guidance'] is None
    assert payload['environmental_impact'] is None
    assert 'decision_reason' not in payload['decision']
    assert all(key not in payload for key in ('score', 'probability', 'probabilities'))


@pytest.mark.parametrize('state', ['identified', 'probable', 'unrecognized', 'out_of_scope', 'retake', 'model_unavailable'])
def test_current_service_decision_supersedes_attached_snapshot(monkeypatch, state):
    decision = _fake_decision()
    decision.status = state
    decision.title = 'Título fornecido pelo serviço'
    decision.suggested_class = 'metal' if state in ('identified', 'probable') else None
    raw = _result(_fake_decision())
    raw.decision.title = 'Snapshot antigo não deve controlar a apresentação'
    monkeypatch.setattr(module, 'analyze_waste_image', lambda *args, **kwargs: raw)
    resolver = Mock(return_value=decision)
    monkeypatch.setattr(module, 'decision_for_result', resolver)
    analyzer = module.LiveCameraAnalyzer(load_config(), model_bundle=FakeBundle())
    payload = analyzer.analyze_frame(_image_bytes(Image.new('RGB', (64, 64))))
    assert payload['decision']['status'] == state
    assert payload['decision']['title'] == decision.title
    assert payload['decision']['correction_available']
    assert payload['decision']['requires_confirmation']
    assert not payload['accepted']
    assert payload['top_class'] == decision.suggested_class
    if decision.suggested_class is None:
        assert payload['suggested_target'] is None
    else:
        assert payload['suggested_target']['destination_title'] == 'Lixeira amarela'
    assert payload['detections'][0]['label'] == 'Região visual'
    assert payload['detections'][0]['top_class'] is None
    resolver.assert_called_once_with(raw, analyzer.config)


@pytest.mark.parametrize('failure', [ImageValidationError('private-upload-path'), ModelLoadError('private-model-path')])
def test_analysis_failure_has_safe_state_and_correction(monkeypatch, failure):
    decision = _fake_decision()
    decision.status = 'retake' if isinstance(failure, ImageValidationError) else 'model_unavailable'
    decision.suggested_class = None
    monkeypatch.setattr(module, 'decision_from_error', lambda exc: decision)
    monkeypatch.setattr(module, 'analyze_waste_image', Mock(side_effect=failure))
    recorder = Mock()
    monkeypatch.setattr(module, 'record_decision', recorder)
    analyzer = module.LiveCameraAnalyzer(load_config(), model_bundle=FakeBundle())
    payload = analyzer.analyze_frame(b'input bytes')
    assert not payload['ok']
    assert payload['decision']['status'] == decision.status
    assert payload['decision']['correction_available']
    assert not payload['accepted']
    assert 'private-' not in str(payload)
    recorder.assert_not_called()  # analysis_service owns this event; do not count twice.


def test_model_outage_does_not_prevent_live_page_initialization(monkeypatch):
    monkeypatch.setattr(module, 'load_model_bundle_for_analysis', Mock(side_effect=ModelLoadError('unavailable')))
    analyzer = module.LiveCameraAnalyzer(load_config())
    assert analyzer.model_bundle is None


def test_empty_frame_and_preanalysis_io_failure_are_recorded_once(monkeypatch):
    recorder = Mock()
    monkeypatch.setattr(module, 'record_decision', recorder)
    analyzer = module.LiveCameraAnalyzer(load_config(), model_bundle=FakeBundle())
    empty = analyzer.analyze_frame(b'')
    assert empty['decision']['status'] == 'retake'
    recorder.assert_called_once()
    recorder.reset_mock()
    analyze = Mock()
    monkeypatch.setattr(module, 'analyze_waste_image', analyze)
    monkeypatch.setattr(module.tempfile, 'NamedTemporaryFile', Mock(side_effect=PermissionError('/private/frame')))
    failed = analyzer.analyze_frame(b'bytes')
    assert not failed['ok'] and failed['decision']['correction_available']
    assert '/private/frame' not in str(failed)
    recorder.assert_called_once()
    analyze.assert_not_called()


def test_javascript_only_renders_service_decision_and_always_offers_correction():
    assert 'result.decision' in LIVE_CAMERA_HTML
    assert 'decision.title' in LIVE_CAMERA_HTML
    assert 'decision.primary_action' in LIVE_CAMERA_HTML
    assert 'result.accepted ?' not in LIVE_CAMERA_HTML
    assert 'item.accepted ?' not in LIVE_CAMERA_HTML
    assert 'categoria confirmada' not in LIVE_CAMERA_HTML
    assert 'id="manualCorrection"' in LIVE_CAMERA_HTML
    assert 'Corrigir ou confirmar material no aplicativo' in LIVE_CAMERA_HTML
