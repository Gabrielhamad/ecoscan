from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ecoscan.config import AppConfig


ENGINE = "semantic_onnx_assisted"


class ModelLoadError(RuntimeError):
    """Raised when the configured recognition release cannot be trusted or loaded."""


@dataclass(frozen=True)
class RecognitionModel:
    classifier: Any
    class_names: tuple[str, ...]
    path: Path
    model_type: str = ENGINE


def configured_model_path(config: AppConfig) -> Path:
    engine = str(config.model.get("engine", ""))
    if engine != ENGINE:
        raise ModelLoadError(
            f"Motor de reconhecimento não suportado: {engine or 'não configurado'}."
        )
    relative_path = str(config.model.get("artifact_path", "")).strip()
    if not relative_path:
        raise ModelLoadError("Caminho do modelo atual não configurado.")
    return config.project_root / relative_path


def resolve_model_path(
    config: AppConfig,
    override: str | Path | None = None,
) -> Path:
    if override is not None:
        path = Path(override)
    else:
        from ecoscan.services.published_model import published_model

        path = published_model(config) or configured_model_path(config)
    if path.name != "semantic.json":
        raise ModelLoadError("O runtime aceita somente releases semânticos ONNX validados.")
    return path


def load_recognition_model(config: AppConfig, path: str | Path) -> RecognitionModel:
    from ecoscan.classification.semantic_onnx import load_semantic_model

    model_path = Path(path)
    if not model_path.is_file():
        raise ModelLoadError(f"Modelo atual não encontrado: {model_path}")
    try:
        classifier = load_semantic_model(
            str(model_path.resolve()),
            str(config.directories["models"] / "semantic-v1"),
        )
    except Exception as exc:
        raise ModelLoadError(f"Falha ao carregar o modelo atual: {model_path}") from exc

    expected = set(config.classes) | {"unknown"}
    actual = {str(item) for item in classifier.classes}
    if actual != expected:
        raise ModelLoadError(
            "Modelo incompatível com o escopo atual. "
            f"Faltam: {sorted(expected - actual) or 'nenhuma'}; "
            f"classes inesperadas: {sorted(actual - expected) or 'nenhuma'}."
        )
    return RecognitionModel(classifier, tuple(config.classes), model_path)
