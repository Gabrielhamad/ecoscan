"""The experimental PDI controls must not change the released RGB profile."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
from PIL import Image, ImageOps
import pytest

from ecoscan.app.pipeline import default_processing_options, run_processing_pipeline
from ecoscan.classification.runtime import ModelLoadError
from ecoscan.classification.prediction import ClassificationPrediction
from ecoscan.config import load_config
from ecoscan.image_processing.adaptive_filters import apply_adaptive_filter_pipeline
from ecoscan.image_processing.preprocessing import letterbox_image, prepare_working_image
from ecoscan.services.analysis_service import analyze_waste_image
from ecoscan.services.processing_evidence import evidence_manifest, processing_evidence


@pytest.fixture
def photo(tmp_path):
    pixels = np.full((160, 240, 3), 220, dtype=np.uint8)
    pixels[30:130, 60:180] = (35, 70, 120)
    pixels[::7, ::7] = 255
    path = tmp_path / 'synthetic.png'
    Image.fromarray(pixels).save(path)
    return path


@pytest.mark.parametrize('filter_name', ['none', 'median', 'gaussian', 'clahe', 'bilateral', 'sobel', 'canny'])
def test_didactic_filters_preserve_official_input_and_contract(photo, filter_name):
    config = load_config()
    baseline = run_processing_pipeline(photo, config)
    options = replace(default_processing_options(config), filter_name=filter_name,
                      segmentation_name='none', morphology_name='none')
    experimental = run_processing_pipeline(photo, config, options)
    np.testing.assert_array_equal(experimental.recognition_image, baseline.recognition_image)
    assert experimental.metadata['recognition_preparation']['contract'] == baseline.metadata['recognition_preparation']['contract']
    assert experimental.capture_quality == baseline.capture_quality
    assert experimental.diagnostic_processing.filter_result is experimental.filter_result
    assert experimental.recognition_preparation.image is experimental.recognition_image
    if filter_name == 'gaussian':
        assert not np.array_equal(experimental.filter_result.image, baseline.filter_result.image)


def test_released_rgb_profile_exif_padding_and_checksum(tmp_path):
    config = load_config()
    path = tmp_path / 'oriented.jpg'
    pixels = np.full((80, 160, 3), (140, 60, 30), dtype=np.uint8)
    pixels[10:50, 30:120] = (30, 80, 150)
    pixels[::11, ::11] = 200
    exif = Image.Exif()
    exif[274] = 6
    Image.fromarray(pixels).save(path, exif=exif)
    with Image.open(path) as image:
        oriented = np.asarray(ImageOps.exif_transpose(image).convert('RGB'))
    working = prepare_working_image(oriented, 640)
    official = apply_adaptive_filter_pipeline(working.resized, config.filters).filter_result.image
    expected, _ = letterbox_image(official, (224, 224), 127)
    result = run_processing_pipeline(path, config)
    np.testing.assert_array_equal(result.loaded.array, oriented)
    np.testing.assert_array_equal(result.recognition_image, expected)
    assert result.recognition_image.shape == (224, 224, 3)
    assert result.recognition_image.dtype == np.uint8
    assert np.all(result.recognition_image[:, :56] == 127)
    metadata = result.metadata['recognition_preparation']
    assert metadata['rgb_sha256'] == hashlib.sha256(expected.tobytes()).hexdigest()
    release = json.loads(Path('models/semantic-v1/semantic.json').read_text())
    assert metadata['contract'] == release['processing']


@pytest.mark.parametrize('change', ['missing', 'checksum', 'profile'])
def test_incompatible_artifact_does_not_run_encoder(photo, change):
    release = json.loads(Path('models/semantic-v1/semantic.json').read_text())
    contract = release['processing']
    if change == 'missing':
        contract = {}
    elif change == 'checksum':
        contract['sha256'] = '0' * 64
    else:
        contract['profile']['padding_rgb'] = 0
    classifier = SimpleNamespace(metadata={'processing': contract}, predict_image=Mock())
    bundle = SimpleNamespace(classifier=classifier, model_type='semantic_onnx_assisted')
    with pytest.raises(ModelLoadError, match='preparação'):
        analyze_waste_image(photo, load_config(), model_bundle=bundle)
    classifier.predict_image.assert_not_called()


def test_manual_experiment_remains_compatible_in_analysis_service(photo):
    release = json.loads(Path('models/semantic-v1/semantic.json').read_text())
    predict = Mock(return_value=ClassificationPrediction('metal', 'metal', .99, {'metal': .99}, True, .8))
    bundle = SimpleNamespace(classifier=SimpleNamespace(metadata=release, predict_image=predict),
                             model_type='semantic_onnx_assisted')
    config = load_config()
    baseline = analyze_waste_image(photo, config, model_bundle=bundle)
    options = replace(default_processing_options(config), filter_name='gaussian',
                      filter_parameters={'kernel_size': 9, 'sigma': 3.0},
                      segmentation_name='hsv_color', morphology_name='erosion',
                      morphology_parameters={'kernel_size': 7})
    experiment = analyze_waste_image(photo, config, options=options, model_bundle=bundle)
    assert experiment.processing_compatible
    assert not experiment.accepted  # Confirmation remains mandatory.
    np.testing.assert_array_equal(predict.call_args_list[0].args[0], predict.call_args_list[1].args[0])
    np.testing.assert_array_equal(baseline.pipeline.loaded.array, experiment.pipeline.loaded.array)
    manifest = evidence_manifest(experiment.pipeline)
    assert manifest['diagnostic_processing']['filter'] == 'gaussian'
    assert not manifest['diagnostic_processing']['affects_recognition']
    assert manifest['recognition_preparation']['contract'] == release['processing']
    assert manifest['classifier_input_sha256'] == evidence_manifest(baseline.pipeline)['classifier_input_sha256']
    assert processing_evidence(experiment.pipeline)[-1].before is experiment.pipeline.recognition_preparation.source


def test_streamlit_experimental_controls_show_both_tracks(photo):
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_string('''
import streamlit as st
from ecoscan.config import load_config
from ecoscan.services.accounts import UserProfile
from ecoscan.ui.processing_configuration import ProcessingSelection, render_public_lab_controls
from ecoscan.ui.processing_lab import render_applied_processing
from ecoscan.app.pipeline import run_processing_pipeline
config = load_config()
selection = render_public_lab_controls(st, config,
    UserProfile('visitor_test', 'Visitante', 'user'), ProcessingSelection('auto'))
pipeline = run_processing_pipeline(st.session_state['photo'], config, selection.to_options())
st.session_state['pipeline'] = pipeline
render_applied_processing(st, pipeline)
''', default_timeout=20)
    app.session_state['photo'] = str(photo)
    app.run()
    assert not app.exception
    before = app.session_state['pipeline']
    app.selectbox(key='public_filter').select('gaussian').run()
    assert not app.exception
    after = app.session_state['pipeline']
    np.testing.assert_array_equal(before.recognition_image, after.recognition_image)
    assert not np.array_equal(before.filter_result.image, after.filter_result.image)
    assert any('processamento experimental' in item.value for item in app.subheader)
    assert any('Preparação para reconhecimento' in item.value for item in app.subheader)
