"""Sondas sintéticas de contrato; não medem acurácia nem usam serviços remotos.

Executar na raiz: python docs/evidencias_auditoria_aps/reproduzir.py
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from types import SimpleNamespace

import numpy as np
from PIL import Image
from streamlit.testing.v1 import AppTest

from ecoscan.app.pipeline import default_processing_options, run_processing_pipeline
from ecoscan.classification.prediction import ClassificationPrediction
from ecoscan.classification.runtime import RecognitionModel
from ecoscan.classification.semantic_onnx import SemanticOnnxClassifier
from ecoscan.config import load_config
from ecoscan.image_processing.contracts import processing_contract
from ecoscan.services.analysis_service import analyze_waste_image
from ecoscan.services.processing_evidence import processing_evidence
from ecoscan.services.recognition_safety import build_recognition_safety_decision


def digest(array):
    return hashlib.sha256(array.tobytes()).hexdigest()


config = load_config()
metadata = json.loads(Path('models/semantic-v1/semantic.json').read_text())
seed = json.loads(Path('models/semantic-v1/learning_seed.json').read_text())
assert metadata['threshold'] == .8
assert metadata['processing'] == seed['processing'] == processing_contract(config)
output = {'synthetic_only': True, 'threshold': metadata['threshold'],
          'default_contract_matches_model_and_seed': True}
with TemporaryDirectory() as temporary:
    path = Path(temporary) / 'synthetic.png'
    rgb = np.full((160, 240, 3), 220, dtype=np.uint8)
    rgb[30:130, 60:180] = (35, 70, 120)
    rgb[::7, ::7] = 255
    Image.fromarray(rgb).save(path)
    default = default_processing_options(config)
    inference = run_processing_pipeline(path, config, default)
    training_options = replace(default, segmentation_name='none', morphology_name='none')
    training = run_processing_pipeline(path, config, training_options)
    np.testing.assert_array_equal(inference.recognition_image, training.recognition_image)
    assert processing_evidence(inference)[-1].after is inference.recognition_image
    output['default_inference_training_rgb_equal'] = True
    output['laboratory_evidence_uses_inference_array'] = True
    # Exercise Streamlit's public selector and its rerun, then the same options adapter.
    app = AppTest.from_string('''
import streamlit as st
from ecoscan.config import load_config
from ecoscan.services.accounts import UserProfile
from ecoscan.ui.processing_configuration import ProcessingSelection, render_public_lab_controls
selection = render_public_lab_controls(st, load_config(),
    UserProfile('visitor_audit', 'Visitante', 'user'), ProcessingSelection('auto'))
st.session_state['audit_options'] = selection.to_options()
''').run()
    assert not app.exception
    tensors = {}
    # Capture the exact normalized tensor at session.run; no neural scores are fabricated.
    encoder = SemanticOnnxClassifier.__new__(SemanticOnnxClassifier)
    encoder.lock = Lock()
    captured = []
    encoder.session = SimpleNamespace(run=lambda _, feed: captured.append(feed['image'].copy())
                                     or [np.zeros((1, 512), dtype=np.float32)])
    for name in ('none', 'median', 'gaussian', 'sobel', 'canny'):
        app.selectbox(key='public_filter').select(name).run()
        assert not app.exception
        result = run_processing_pipeline(path, config, app.session_state['audit_options'])
        encoder.image_features(result.recognition_image)
        tensors[name] = captured[-1]
        output[name] = {'rgb_sha256': digest(result.recognition_image),
                        'encoder_tensor_sha256': digest(captured[-1]),
                        'contract_matches_model': result.metadata['recognition_preparation']['contract'] == metadata['processing']}
    assert not np.array_equal(tensors['none'], tensors['median'])
    assert not np.array_equal(tensors['none'], tensors['gaussian'])
    for name in ('sobel', 'canny'):
        np.testing.assert_array_equal(tensors['none'], tensors[name])
    # Controlled accepted prediction isolates service policy from model accuracy.
    prediction = ClassificationPrediction('metal', 'metal', .99, {'metal': .99}, True, .8)
    classifier = SimpleNamespace(metadata=metadata, predict_image=lambda _: prediction)
    bundle = RecognitionModel(classifier, tuple(config.classes), Path('models/semantic-v1/semantic.json'))
    policy = {}
    for required in (True, False):
        cfg = replace(config, model={**config.model, 'confirmation_required': required})
        result = analyze_waste_image(path, cfg, model_bundle=bundle,
                                    model_path=bundle.path, options=default)
        assert result.processing_compatible
        assert result.accepted is (not required)
        assert result.top_class == 'metal'
        decision = build_recognition_safety_decision(result)
        assert not decision.allow_disposal_guidance
        policy[str(required)] = {'accepted': result.accepted, 'predicted_class': result.predicted_class,
                                 'safety_status': decision.status, 'guidance_allowed': decision.allow_disposal_guidance}
    output['controlled_prediction_policy'] = policy
print(json.dumps(output, indent=2))
