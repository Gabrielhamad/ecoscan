"""Public flow regressions use synthetic pixels and local service stubs only."""
import io
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
from PIL import Image
import pytest
from streamlit.testing.v1 import AppTest

from ecoscan.config import load_config
from ecoscan.services.accounts import UserProfile
from ecoscan.ui.common_views import _render_user_error
from ecoscan.ui.app_resources import load_app_resources


class Upload:
    def __init__(self, data, name='fixture.png'):
        self.data = data
        self.name = name
        self.size = len(data)

    def getvalue(self):
        return self.data

    def getbuffer(self):
        return memoryview(self.data)


def public_app(upload=None, result=None, profile=None, missing_guidance=False):
    app = AppTest.from_string('''
import streamlit as st
from unittest.mock import patch
from ecoscan.ui.analysis_controller import render_analysis_page
from ecoscan.ui.session_state import AnalysisSession
from ecoscan.app.processing_options import ProcessingPipelineOptions
from ecoscan.services.accounts import UserProfile
with patch.object(st, 'file_uploader', return_value=st.session_state.test_upload):
    render_analysis_page(st, st.container(), st.session_state.test_config,
        st.session_state.test_profile, st.session_state.test_guidance,
        st.session_state.test_targets, {}, (), ProcessingPipelineOptions(), False,
        AnalysisSession(st.session_state))
''', default_timeout=20)
    config = load_config()
    resources = load_app_resources(config)
    app.session_state['test_upload'] = upload
    app.session_state['test_config'] = config
    app.session_state['test_profile'] = profile or UserProfile('visitor_test', 'Visitante', 'user')
    app.session_state['test_guidance'] = {} if missing_guidance else resources.guidance_by_class
    app.session_state['test_targets'] = resources.targets_by_class
    if result is not None:
        app.session_state['last_analysis_result'] = result
        app.session_state['last_analysis_signature'] = 'captured'
        app.session_state['last_analysis_source'] = 'upload'
    return app


def test_public_error_never_renders_or_logs_raw_exception(caplog):
    private = '/private/photo.png token=secret citizen@example.org protocol-123'
    st = MagicMock()
    _render_user_error(st, RuntimeError(private), context='image_analysis')
    assert private not in caplog.text
    assert private not in str(st.mock_calls)
    st.code.assert_not_called()


def test_empty_capture_allows_manual_disposal():
    app = public_app().run()
    assert not app.exception
    assert any('material' in item.label.lower() for item in app.selectbox)


@pytest.fixture
def upload():
    pixels = np.full((64, 80, 3), 235, np.uint8)
    pixels[12:50, 18:60] = (30, 90, 50)
    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, format='PNG')
    return Upload(buffer.getvalue())


@pytest.fixture
def result(upload, tmp_path):
    from ecoscan.app.pipeline import run_processing_pipeline
    from ecoscan.services.analysis_service import WasteAnalysisResult
    path = tmp_path / 'fixture.png'
    path.write_bytes(upload.data)
    pipeline = run_processing_pipeline(path, load_config())
    return WasteAnalysisResult(pipeline, None, 'metal', .9, False, 'Hipótese automática', None,
                               {'metal': .9, 'glass': .1}, 'semantic_onnx_assisted')


def _manual(app):
    return next(item for item in app.selectbox if item.label == 'Qual material você confirmou?')


def _messages(app):
    return ' '.join(str(item.value) for group in (app.markdown, app.caption, app.success,
                                                app.error, app.info, app.warning, app.subheader) for item in group)


@pytest.mark.parametrize('failure', ['load', 'inference', 'network'])
def test_model_failure_preserves_pdi_with_public_opt_in_but_strict_call_raises(upload, tmp_path, failure, caplog):
    from ecoscan.classification.runtime import ModelLoadError
    from ecoscan.services.analysis_service import analyze_waste_image
    from ecoscan.services.recognition_safety import build_recognition_safety_decision
    path = tmp_path / 'fixture.png'
    path.write_bytes(upload.data)
    private = 'token=private citizen@example.org /private/photo.png protocol-xyz'
    bundle = SimpleNamespace(model_type='semantic_onnx_assisted')
    target = 'load_recognition_model' if failure != 'inference' else '_predict'
    error = (ModelLoadError(private) if failure == 'load' else
             ConnectionError(private) if failure == 'network' else RuntimeError(private))
    with patch('ecoscan.services.analysis_service.' + target, side_effect=error):
        options = {'model_bundle': bundle} if failure == 'inference' else {}
        recovered = analyze_waste_image(path, load_config(), allow_model_fallback=True, **options)
        with pytest.raises(type(error)):
            analyze_waste_image(path, load_config(), **options)
    assert recovered.model_type == 'unavailable'
    assert recovered.top_class is None and recovered.predicted_class is None
    assert not recovered.accepted and recovered.guidance is None
    assert recovered.probabilities == {} and recovered.elapsed_ms >= 0
    assert recovered.pipeline.loaded.array.shape == (64, 80, 3)
    decision = build_recognition_safety_decision(recovered)
    assert decision.status == 'model_unavailable' and not decision.allow_disposal_guidance
    assert private not in caplog.text
    assert any(getattr(record, 'event', '') == 'recognition_unavailable' for record in caplog.records)


def test_public_fallback_does_not_accept_invalid_image(tmp_path):
    from ecoscan.image_processing.validation import ImageValidationError
    from ecoscan.services.analysis_service import analyze_waste_image
    path = tmp_path / 'invalid.png'
    path.write_bytes(b'corrupted')
    with pytest.raises(ImageValidationError):
        analyze_waste_image(path, load_config(), allow_model_fallback=True)


@pytest.mark.parametrize('compatible', [True, False])
def test_hypothesis_manual_correction_and_special_disposal_remain_separate(upload, result, compatible):
    result = replace(result, processing_compatible=compatible)
    app = public_app(upload=upload)
    with patch('ecoscan.services.analysis_service.analyze_waste_image', return_value=result) as analyze:
        app.run()
        assert not app.exception
        assert 'Melhor correspondência: Metal' in _messages(app)
        assert not app.success
        _manual(app).select('glass').run()
        assert not app.exception
        assert 'Material confirmado por você: Vidro' in _messages(app)
        assert 'Lixeira verde' in _messages(app)
        assert any(item.label == 'Ponto específico' for item in app.get('link_button'))
        _manual(app).select('battery').run()
        assert not app.exception
        assert 'Ponto' in _messages(app)
        assert result.top_class == 'metal' and not result.accepted
        assert analyze.call_count == 1
        assert analyze.call_args.kwargs['allow_model_fallback']
        assert not analyze.call_args.args[0].exists()  # temporary upload removed


@pytest.mark.parametrize('case', ['empty', 'corrupt', 'extension', 'oversized'])
def test_invalid_upload_still_allows_manual_and_does_not_repeat_or_leak(case, upload):
    if case == 'empty':
        upload = Upload(b'')
    elif case == 'corrupt':
        upload = Upload(b'not an image')
    elif case == 'extension':
        upload.name = 'citizen@example.org.exe'
    else:
        upload.size = 16 * 1024 * 1024
        upload.getvalue = MagicMock(side_effect=AssertionError('must reject before copying bytes'))
    app = public_app(upload=upload).run()
    assert not app.exception
    assert app.error
    _manual(app).select('metal').run()
    assert not app.exception
    assert 'Material confirmado por você: Metal' in _messages(app)
    assert 'citizen@example.org' not in _messages(app)
    if case == 'oversized':
        upload.getvalue.assert_not_called()


def test_cached_result_survives_empty_widget_and_new_capture_clears_confirmation(result):
    app = public_app(result=result).run()
    assert not app.exception
    assert 'Melhor correspondência: Metal' in _messages(app)
    _manual(app).select('glass').run()
    assert 'Material confirmado por você: Vidro' in _messages(app)
    app.button(key='new_analysis').click().run()
    assert not app.exception
    assert _manual(app).value is None
    assert app.session_state['analysis_capture_generation'] == 1
    assert 'Melhor correspondência: Metal' not in _messages(app)


def test_new_photo_does_not_inherit_previous_human_confirmation(upload, result):
    app = public_app(upload=upload)
    with patch('ecoscan.services.analysis_service.analyze_waste_image', return_value=result) as analyze:
        app.run()
        _manual(app).select('metal').run()
        buffer = io.BytesIO()
        Image.new('RGB', (64, 64), 'blue').save(buffer, format='PNG')
        app.session_state['test_upload'] = Upload(buffer.getvalue(), 'second.png')
        app.run()
        assert not app.exception
        assert _manual(app).value is None
        assert not app.success
        assert analyze.call_count == 2


def test_retry_model_and_optional_processing_failure_keep_correction(upload, result):
    unavailable = replace(result, model_type='unavailable', top_class=None, probabilities={})
    app = public_app(upload=upload)
    with patch('ecoscan.services.analysis_service.analyze_waste_image', side_effect=[unavailable, result]) as analyze:
        with patch('ecoscan.ui.processing_lab.render_applied_processing', side_effect=OSError('/private/export.png')):
            app.run()
            assert not app.exception
            assert 'Reconhecimento indisponível' in _messages(app)
            _manual(app).select('plastic').run()
            assert 'Material confirmado por você: Plástico' in _messages(app)
            app.button(key='retry_analysis').click().run()
            assert not app.exception
            assert 'Melhor correspondência: Metal' in _messages(app)
            assert analyze.call_count == 2
            assert _manual(app).value is None
            assert '/private/export.png' not in _messages(app)


def test_missing_reference_data_is_explicit_empty_state():
    app = public_app(missing_guidance=True).run()
    assert not app.exception
    assert _manual(app).options == ['Selecione o material (confirmação manual)']
    assert 'Orientações locais indisponíveis' in _messages(app)


def test_exif_is_corrected_before_model_failure_and_original_is_kept(tmp_path):
    from ecoscan.services.analysis_service import analyze_waste_image
    from PIL import ImageOps
    image = Image.new('RGB', (80, 64), 'white')
    image.paste('red', (0, 0, 40, 32))
    exif = image.getexif()
    exif[274] = 6
    path = tmp_path / 'rotated.jpg'
    image.save(path, exif=exif)
    with Image.open(path) as encoded:
        expected = np.array(ImageOps.exif_transpose(encoded).convert('RGB'))
    with patch('ecoscan.services.analysis_service.load_recognition_model', side_effect=OSError('unavailable')):
        result = analyze_waste_image(path, load_config(), allow_model_fallback=True)
    np.testing.assert_array_equal(result.pipeline.loaded.array, expected)
    assert expected.shape == (80, 64, 3)


def test_authorized_contribution_database_failure_does_not_block_manual_or_leak(upload, result, tmp_path, caplog):
    profile = UserProfile('supabase_test', 'Pessoa', 'user')
    app = public_app(upload=upload, profile=profile)
    config = load_config()
    app.session_state['test_config'] = replace(config, history={'enabled': False})
    private = 'token=secret citizen@example.org /private/photo.png protocol-123'
    with (patch('ecoscan.services.analysis_service.analyze_waste_image', return_value=result),
          patch('ecoscan.ui.learning.submit_contribution', side_effect=RuntimeError(private)) as submit):
        app.run()
        next(item for item in app.selectbox if item.label == 'O que aparece na foto?').select('drink_can')
        app.checkbox[0].check()
        next(item for item in app.button if item.label == 'Enviar correção').click().run()
        assert not app.exception
        assert 'Envio não confirmado' in _messages(app)
        assert private not in _messages(app) and private not in caplog.text
        _manual(app).select('glass').run()
        assert 'Material confirmado por você: Vidro' in _messages(app)
        assert submit.call_count == 1  # no implicit retry of an uncertain write


def test_huge_pixel_image_is_rejected_without_losing_manual_disposal():
    # 1-bit PNG is compact on disk; its dimensions exceed the existing 40 MP gate.
    buffer = io.BytesIO()
    Image.new('1', (6400, 6400)).save(buffer, format='PNG')
    app = public_app(upload=Upload(buffer.getvalue())).run()
    assert not app.exception
    assert any('IMG-001' in item.value for item in app.error)
    _manual(app).select('metal').run()
    assert not app.exception
    assert 'Material confirmado por você: Metal' in _messages(app)


def test_missing_target_does_not_claim_destination():
    app = public_app()
    app.session_state['test_targets'] = {}
    app.run()
    _manual(app).select('metal').run()
    assert not app.exception
    assert not app.success
    assert 'destino deste material está indisponível' in _messages(app)
