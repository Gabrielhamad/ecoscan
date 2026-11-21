"""Integration regressions use technical pixels/stubs, never field accuracy evidence."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image
import pytest
from streamlit.testing.v1 import AppTest

from ecoscan.app.processing_options import ProcessingPipelineOptions
from ecoscan.classification.prediction import ClassificationPrediction
from ecoscan.classification.runtime import ModelLoadError
from ecoscan.config import AppConfig, load_config
from ecoscan.services.analysis_service import analyze_waste_image
from ecoscan.services.processing_evidence import evidence_manifest
from ecoscan.services.recognition_safety import build_recognition_safety_decision
from test_public_resilience import Upload, _manual, _messages, public_app


@pytest.fixture
def isolated_config(monkeypatch: pytest.MonkeyPatch) -> AppConfig:
    monkeypatch.setenv("ECOSCAN_REMOTE_MODELS", "false")
    monkeypatch.setattr("streamlit.secrets", {})
    config = load_config()
    return replace(config, model={**config.model, "remote_models_enabled": False})


def _photo(path: Path, *, dark: bool = False) -> Path:
    if dark:
        pixels = np.zeros((96, 128, 3), dtype=np.uint8)
        pixels[30, 40] = 1
    else:
        pixels = np.full((96, 128, 3), 220, dtype=np.uint8)
        pixels[20:80, 35:95] = (35, 70, 120)
        pixels[::7, ::7] = 255
    Image.fromarray(pixels).save(path)
    return path


def _bundle(config: AppConfig, label: str = "metal") -> SimpleNamespace:
    metadata = json.loads((config.project_root / "models/semantic-v1/semantic.json").read_text())
    scores = {class_id: 0.0 for class_id in (*config.classes, "unknown")}
    scores[label] = 0.99
    scores["unknown" if label != "unknown" else "metal"] = 0.01
    prediction = ClassificationPrediction(
        label,
        label if label != "unknown" else None,
        0.99,
        scores,
        label != "unknown",
        0.8,
    )
    return SimpleNamespace(
        model_type="semantic_onnx_assisted",
        classifier=SimpleNamespace(metadata=metadata, predict_image=Mock(return_value=prediction)),
    )


@pytest.mark.parametrize("filter_name", ["gaussian", "median", "sobel"])
@pytest.mark.parametrize("segmentation", ["otsu", "hsv_color"])
@pytest.mark.parametrize("morphology", ["none", "open_close"])
@pytest.mark.parametrize(
    "case,label,expected_state",
    [
        ("supported", "metal", "needs_confirmation"),
        ("unknown", "unknown", "outside_scope"),
        ("dark", "metal", "retake"),
    ],
)
def test_combined_experiments_preserve_encoder_and_safe_decision(
    tmp_path: Path,
    isolated_config: AppConfig,
    filter_name: str,
    segmentation: str,
    morphology: str,
    case: str,
    label: str,
    expected_state: str,
) -> None:
    path = _photo(tmp_path / "technical.png", dark=case == "dark")
    bundle = _bundle(isolated_config, label)
    model_path = isolated_config.project_root / "models/semantic-v1/semantic.json"
    control = analyze_waste_image(
        path,
        isolated_config,
        model_path=model_path,
        model_bundle=bundle,
        options=ProcessingPipelineOptions(
            filter_name="none", segmentation_name="none", morphology_name="none"
        ),
    )
    parameters = (
        {"kernel_size": 5, "sigma": 1.5}
        if filter_name == "gaussian"
        else ({"kernel_size": 3} if filter_name == "median" else {})
    )
    experiment = analyze_waste_image(
        path,
        isolated_config,
        model_path=model_path,
        model_bundle=bundle,
        options=ProcessingPipelineOptions(
            filter_name=filter_name,
            filter_parameters=parameters,
            segmentation_name=segmentation,
            morphology_name=morphology,
            morphology_parameters={"kernel_size": 3, "iterations": 1},
        ),
    )

    calls = bundle.classifier.predict_image.call_args_list
    assert len(calls) == 2
    np.testing.assert_array_equal(calls[0].args[0], calls[1].args[0])
    np.testing.assert_array_equal(control.pipeline.loaded.array, experiment.pipeline.loaded.array)
    before = control.pipeline.metadata["recognition_preparation"]
    after = experiment.pipeline.metadata["recognition_preparation"]
    assert (
        after["rgb_sha256"]
        == before["rgb_sha256"]
        == hashlib.sha256(calls[1].args[0].tobytes(order="C")).hexdigest()
    )
    assert after["contract"] == before["contract"] == bundle.classifier.metadata["processing"]
    assert experiment.pipeline.capture_quality == control.pipeline.capture_quality
    assert build_recognition_safety_decision(control) == build_recognition_safety_decision(
        experiment
    )
    decision = build_recognition_safety_decision(experiment)
    assert decision.status == expected_state
    assert not decision.allow_disposal_guidance and not experiment.accepted
    assert (
        experiment.top_class == control.top_class
        and experiment.probabilities == control.probabilities
    )
    assert experiment.processing_compatible and not after["mask_applied"]
    assert not np.array_equal(
        control.pipeline.filter_result.image, experiment.pipeline.filter_result.image
    )
    manifest = evidence_manifest(experiment.pipeline)
    assert (
        manifest["classifier_input_sha256"]
        == evidence_manifest(control.pipeline)["classifier_input_sha256"]
    )
    assert manifest["diagnostic_processing"]["filter"] == filter_name
    assert not manifest["diagnostic_processing"]["affects_recognition"]


@pytest.mark.parametrize("change", ["missing", "checksum", "profile"])
def test_contract_rejection_preserves_public_pdi_without_invoking_encoder(
    tmp_path: Path,
    isolated_config: AppConfig,
    change: str,
) -> None:
    path = _photo(tmp_path / "technical.png")
    bundle = _bundle(isolated_config)
    if change == "missing":
        bundle.classifier.metadata.pop("processing")
    elif change == "checksum":
        bundle.classifier.metadata["processing"]["sha256"] = "0" * 64
    else:
        bundle.classifier.metadata["processing"]["profile"]["padding_rgb"] = 0
    model_path = isolated_config.project_root / "models/semantic-v1/semantic.json"
    result = analyze_waste_image(
        path,
        isolated_config,
        model_path=model_path,
        model_bundle=bundle,
        allow_model_fallback=True,
        options=ProcessingPipelineOptions(
            filter_name="sobel", segmentation_name="otsu", morphology_name="open_close"
        ),
    )
    assert result.pipeline.diagnostic_processing.filter_result.name == "sobel"
    assert result.pipeline.recognition_image.shape == (224, 224, 3)
    assert evidence_manifest(result.pipeline)["stages"]
    assert result.model_type == "unavailable" and not result.processing_compatible
    assert result.top_class is None and result.probabilities == {} and not result.accepted
    decision = build_recognition_safety_decision(result)
    assert decision.status == "model_unavailable" and not decision.allow_disposal_guidance
    with pytest.raises(ModelLoadError, match="preparação"):
        analyze_waste_image(path, isolated_config, model_path=model_path, model_bundle=bundle)
    bundle.classifier.predict_image.assert_not_called()


def test_real_missing_encoder_keeps_public_pipeline_and_manual_disposal(
    tmp_path: Path,
    isolated_config: AppConfig,
) -> None:
    folder = tmp_path / "models/semantic-v1"
    folder.mkdir(parents=True)
    for name in ("semantic.json", "head.npz"):
        shutil.copyfile(isolated_config.project_root / "models/semantic-v1" / name, folder / name)
    config = replace(
        isolated_config,
        directories={**isolated_config.directories, "models": folder.parent},
        model={**isolated_config.model, "artifact_path": str(folder / "semantic.json")},
    )
    photo = _photo(tmp_path / "technical.png")
    assert not list(folder.glob("*.part")) and not (folder / "encoder.onnx").exists()
    with pytest.raises(ModelLoadError):
        analyze_waste_image(photo, config)
    app = public_app(upload=Upload(photo.read_bytes()))
    app.session_state["test_config"] = config
    app.run()
    assert not app.exception
    result = app.session_state["last_analysis_result"]
    assert result.model_type == "unavailable" and not result.accepted
    assert result.pipeline.recognition_image.shape == (224, 224, 3)
    assert "Reconhecimento indisponível" in _messages(app)
    assert any("processamento experimental" in item.value for item in app.subheader)
    _manual(app).select("glass").run()
    assert not app.exception
    assert "Material confirmado por você: Vidro" in _messages(app)
    assert "Lixeira verde" in _messages(app)
    assert not (folder / "encoder.onnx").exists()


def test_filter_change_reprocesses_pdi_and_clears_previous_human_confirmation(
    tmp_path: Path,
    isolated_config: AppConfig,
) -> None:
    photo = _photo(tmp_path / "technical.png")
    app = AppTest.from_string(
        """
import streamlit as st
from unittest.mock import patch
from ecoscan.services.accounts import UserProfile
from ecoscan.ui.app_resources import load_app_resources
from ecoscan.ui.analysis_controller import render_analysis_page
from ecoscan.ui.processing_configuration import ProcessingSelection, render_public_lab_controls
from ecoscan.ui.session_state import AnalysisSession
config = st.session_state.test_config
profile = UserProfile("visitor_integrated", "Visitante", "user")
resources = load_app_resources(config)
selection = render_public_lab_controls(st, config, profile, ProcessingSelection("auto"))
with patch.object(st, "file_uploader", return_value=st.session_state.test_upload):
    render_analysis_page(st, st.container(), config, profile, resources.guidance_by_class,
        resources.targets_by_class, {}, (), selection.to_options(), False,
        AnalysisSession(st.session_state))
""",
        default_timeout=20,
    )
    app.session_state["test_config"] = isolated_config
    app.session_state["test_upload"] = Upload(photo.read_bytes())
    bundle = _bundle(isolated_config)
    with patch("ecoscan.services.analysis_service.load_recognition_model", return_value=bundle):
        app.run()
        assert not app.exception
        before = app.session_state["last_analysis_result"]
        signature = app.session_state["last_analysis_signature"]
        _manual(app).select("glass").run()
        assert "Material confirmado por você: Vidro" in _messages(app)
        app.selectbox(key="public_filter").select("gaussian").run()
    assert not app.exception
    after = app.session_state["last_analysis_result"]
    assert app.session_state["last_analysis_signature"] != signature
    assert _manual(app).value is None and not app.success
    assert after.top_class == before.top_class == "metal" and not after.accepted
    np.testing.assert_array_equal(
        before.pipeline.recognition_image, after.pipeline.recognition_image
    )
    assert (
        before.pipeline.metadata["recognition_preparation"]["rgb_sha256"]
        == after.pipeline.metadata["recognition_preparation"]["rgb_sha256"]
    )
    assert not np.array_equal(
        before.pipeline.filter_result.image, after.pipeline.filter_result.image
    )
    assert bundle.classifier.predict_image.call_count == 2


@pytest.mark.parametrize(
    "material,destination",
    [("battery", "Ponto de coleta especial"), ("electronic", "Ponto de logística reversa")],
)
def test_standalone_manual_consultation_requires_human_choice_for_special_materials(
    isolated_config: AppConfig,
    material: str,
    destination: str,
) -> None:
    app = AppTest.from_string(
        """
import streamlit as st
from ecoscan.ui.app_resources import load_app_resources
from ecoscan.ui.disposal_views import render_manual_disposal
config = st.session_state.test_config
resources = load_app_resources(config)
st.subheader("Descarte responsável")
st.session_state.selected = render_manual_disposal(
    st, config, resources.guidance_by_class, resources.targets_by_class,
    resources.impacts_by_class, resources.collection_points,
    selection_key="manual_disposal_consultation",
)
""",
        default_timeout=20,
    )
    app.session_state["test_config"] = isolated_config
    with (
        patch("ecoscan.services.analysis_service.analyze_waste_image") as analyze,
        patch("ecoscan.services.contribution_store.remote_store") as store,
    ):
        app.run()
        assert not app.exception
        assert app.session_state["selected"] is None and not app.success
        _manual(app).select(material).run()
        analyze.assert_not_called()
        store.assert_not_called()
    assert not app.exception
    assert app.session_state["selected"] == material
    assert len(app.success) == 1 and destination in app.success[0].value
    assert "Material confirmado por você:" in app.success[0].value
    assert "Lixeira" not in app.success[0].value
    assert "Material identificado" not in _messages(app)
