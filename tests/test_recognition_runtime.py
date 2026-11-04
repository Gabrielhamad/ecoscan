from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ecoscan.classification.runtime import (
    ENGINE,
    ModelLoadError,
    configured_model_path,
    load_recognition_model,
    resolve_model_path,
)
from ecoscan.config import load_config


def config_with(tmp_path: Path, **model):
    config = load_config()
    return replace(
        config,
        project_root=tmp_path,
        directories={**config.directories, "models": tmp_path / "models"},
        model={"engine": ENGINE, "artifact_path": "models/current/semantic.json", **model},
    )


def test_runtime_rejects_unconfigured_engine(tmp_path):
    config = config_with(tmp_path, engine="unsupported")
    with pytest.raises(ModelLoadError, match="não suportado"):
        configured_model_path(config)


def test_runtime_rejects_non_semantic_override(tmp_path):
    with pytest.raises(ModelLoadError, match="somente releases"):
        resolve_model_path(config_with(tmp_path), tmp_path / "model.joblib")


def test_runtime_reports_missing_release(tmp_path):
    with pytest.raises(ModelLoadError, match="não encontrado"):
        load_recognition_model(config_with(tmp_path), tmp_path / "semantic.json")


def test_runtime_rejects_incompatible_classes(tmp_path):
    path = tmp_path / "semantic.json"
    path.write_text("{}", encoding="utf-8")
    classifier = SimpleNamespace(classes=("metal", "unknown"))
    with patch(
        "ecoscan.classification.semantic_onnx.load_semantic_model",
        return_value=classifier,
    ):
        with pytest.raises(ModelLoadError, match="incompatível"):
            load_recognition_model(config_with(tmp_path), path)
