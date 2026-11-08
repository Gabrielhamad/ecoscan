"""Presentation tests only: service decisions are injected, never used as ML evidence."""
from types import SimpleNamespace

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from ecoscan.services.recognition_safety import RecognitionSafetyDecision


APP = '''
from dataclasses import replace
from unittest.mock import patch
import streamlit as st
from ecoscan.config import load_config
from ecoscan.services.accounts import UserProfile
from ecoscan.disposal.guidance import load_guidance
from ecoscan.disposal.targets import load_disposal_targets
from ecoscan.ui.analysis_controller import render_analysis_page
from ecoscan.ui.session_state import AnalysisSession
from ecoscan.app.processing_options import default_processing_options
from tests.test_streamlit_camera_flow import FakeUploadedFile

class Upload(FakeUploadedFile):
    def getbuffer(self):
        return self.getvalue()

config = replace(load_config(), history={'enabled': False})
profile = UserProfile(st.session_state['profile_id'], 'Teste', 'user')
root = config.project_root
guidance = load_guidance(root / 'config/disposal_guidance.json')
targets = load_disposal_targets(root / 'config/disposal_targets.json')
error = st.session_state['analysis_error']
def analyze(*args, **kwargs):
    st.session_state['analysis_calls'] = st.session_state.get('analysis_calls', 0) + 1
    if error is not None:
        raise error
    return st.session_state['analysis_result']
with patch.object(st, 'file_uploader', return_value=Upload('synthetic.png', b'synthetic fixture')), \
     patch('ecoscan.services.analysis_service.analyze_waste_image', side_effect=analyze), \
     patch('ecoscan.ui.analysis_controller.decision_for_result', return_value=st.session_state['service_decision']), \
     patch('ecoscan.ui.processing_lab.render_applied_processing'), \
     patch('ecoscan.ui.analysis_controller._render_capture_quality_advice'), \
     patch('ecoscan.ui.analysis_controller._render_photo_processing_summary'), \
     patch('ecoscan.ui.analysis_controller._render_processing_evidence'), \
     patch('ecoscan.ui.analysis_controller._render_disposal_action_panel',
           side_effect=lambda *args: st.write('MANUAL_DESTINATION:' + args[3].class_id)):
    render_analysis_page(st, st.container(), config, profile, guidance, targets, {}, [],
                         default_processing_options(config), False, AnalysisSession(st.session_state))
'''


def decision_for_state(state):
    # Rendering an identified service result does not authorize it. Gate verification
    # belongs to the service tests; this fixture tests a view with a supplied contract.
    title = {'identified': 'Material identificado: METAL',
             'probable': 'Melhor correspondência: METAL',
             'unrecognized': 'Material não reconhecido',
             'out_of_scope': 'Item fora do escopo',
             'retake': 'Refaça a foto',
             'model_unavailable': 'Reconhecimento indisponível'}[state]
    return RecognitionSafetyDecision(
        status=state, tone='ok' if state == 'identified' else 'warn', title=title,
        message='Confirme para descartar. A foto não comprova composição, limpeza ou conteúdo.',
        primary_action='Confirme ou corrija o material.', allow_disposal_guidance=False,
        encourage_feedback=True, suggested_class='metal' if state in {'identified', 'probable'} else None,
    )


def app_for(profile_id, decision=None, error=None):
    pipeline = SimpleNamespace(loaded=SimpleNamespace(array=np.full((64, 64, 3), 127, dtype=np.uint8)))
    # Raw fields deliberately conflict with the service decision to catch UI bypasses.
    result = SimpleNamespace(pipeline=pipeline, top_class='metal', probability=.99,
                             accepted=True, guidance=None, model_type='semantic_onnx_assisted',
                             decision=decision)
    app = AppTest.from_string(APP, default_timeout=20)
    app.session_state['profile_id'] = profile_id
    app.session_state['analysis_result'] = result
    app.session_state['analysis_error'] = error
    app.session_state['service_decision'] = decision
    return app.run()


def texts(app):
    return '\n'.join(item.value for category in ('warning', 'error', 'success', 'info', 'markdown', 'subheader')
                     for item in getattr(app, category))


@pytest.mark.parametrize('profile_id', ['visitor_fixture', 'supabase_00000000-0000-4000-8000-000000000001'])
@pytest.mark.parametrize('state', ['identified', 'probable', 'unrecognized', 'out_of_scope', 'retake', 'model_unavailable'])
def test_every_decision_keeps_manual_correction_and_does_not_infer_disposal(profile_id, state):
    app = app_for(profile_id, decision_for_state(state))
    assert not app.exception
    assert len([box for box in app.selectbox if box.label == 'Qual material você identificou na foto?']) == 1
    rendered = texts(app)
    assert decision_for_state(state).title in rendered
    assert 'MANUAL_DESTINATION:' not in rendered
    assert '0.99' not in rendered
    if state != 'identified':
        assert 'Material identificado:' not in rendered
    if profile_id.startswith('visitor_'):
        assert not app.checkbox
        assert 'conta verificada' in rendered
    else:
        assert any('Autorizo o grupo' in box.label for box in app.checkbox)
    correction = next(box for box in app.selectbox if box.label == 'Qual material você identificou na foto?')
    correction.select('battery').run()
    assert not app.exception
    assert 'MANUAL_DESTINATION:battery' in texts(app)


@pytest.mark.parametrize('profile_id', ['visitor_fixture', 'supabase_00000000-0000-4000-8000-000000000001'])
@pytest.mark.parametrize('error_kind', ['invalid_image', 'missing_model'])
def test_failed_analysis_keeps_local_manual_correction(profile_id, error_kind):
    from ecoscan.classification.runtime import ModelLoadError
    from ecoscan.image_processing.validation import ImageValidationError
    error = ImageValidationError('Synthetic invalid image') if error_kind == 'invalid_image' else ModelLoadError('Synthetic unavailable model')
    app = app_for(profile_id, error=error)
    assert not app.exception
    assert app.error
    assert 'Material identificado:' not in texts(app)
    correction = next(box for box in app.selectbox if box.label == 'Qual material você identificou na foto?')
    correction.select('metal').run()
    assert not app.exception
    assert 'MANUAL_DESTINATION:metal' in texts(app)
    assert not app.checkbox  # No unusable photo can be submitted as a contribution.



def test_policy_re_evaluation_replaces_cached_identified_message_without_new_inference():
    app = app_for('visitor_fixture', decision_for_state('identified'))
    assert not app.exception
    assert 'Material identificado: METAL' in texts(app)
    assert app.session_state['analysis_calls'] == 1
    app.session_state['service_decision'] = decision_for_state('probable')
    app.run()
    assert not app.exception
    assert app.session_state['analysis_calls'] == 1
    assert 'Material identificado:' not in texts(app)
    assert 'Melhor correspondência: METAL' in texts(app)
