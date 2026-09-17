from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ecoscan.classification.baseline import (
    BaselinePrediction,
    KNearestNeighborsClassifier,
    NearestCentroidClassifier,
)
from ecoscan.classification.features import FeatureConfig, extract_features
from ecoscan.classification.visual_knn import VisualKnnClassifier
from ecoscan.classification.visual_svm import VisualSvmClassifier


class ModelLoadError(RuntimeError):
    """Raised when a model file is missing or cannot be read."""


@dataclass(frozen=True)
class BaselineModelBundle:
    classifier: NearestCentroidClassifier | KNearestNeighborsClassifier
    feature_config: FeatureConfig
    metadata: dict
    model_type: str


@dataclass(frozen=True)
class KerasModelBundle:
    model: object
    class_names: list[str]
    threshold: float
    model_type: str = "tensorflow_keras"


@dataclass(frozen=True)
class VisualKnnModelBundle:
    classifier: VisualKnnClassifier
    metadata: dict
    model_type: str = "visual_knn"


@dataclass(frozen=True)
class VisualSvmModelBundle:
    classifier: VisualSvmClassifier
    metadata: dict
    model_type: str = "visual_svm"


def load_baseline_model(path: str | Path) -> BaselineModelBundle:
    model_path = Path(path)
    if not model_path.exists():
        raise ModelLoadError(f"Modelo baseline não encontrado: {model_path}")
    try:
        payload = json.loads(model_path.read_text(encoding="utf-8"))
        metadata = dict(payload.get("metadata", {}))
        feature_metadata = dict(metadata.get("feature_config", {}))
        feature_config = FeatureConfig(
            image_size=tuple(feature_metadata.get("image_size", [96, 96])),
            histogram_bins=int(feature_metadata.get("histogram_bins", 8)),
        )
        model_type = str(payload.get("type", ""))
        if model_type == "nearest_centroid_baseline":
            classifier = NearestCentroidClassifier.load(model_path)
        elif model_type == "knn_baseline":
            classifier = KNearestNeighborsClassifier.load(model_path)
        else:
            raise ModelLoadError(f"Tipo de modelo baseline não suportado: {model_type}")
    except Exception as exc:
        raise ModelLoadError(f"Falha ao carregar modelo baseline: {model_path}") from exc
    return BaselineModelBundle(
        classifier=classifier,
        feature_config=feature_config,
        metadata=metadata,
        model_type=model_type,
    )


def predict_with_baseline(image: np.ndarray, bundle: BaselineModelBundle) -> BaselinePrediction:
    features = extract_features(image, bundle.feature_config)
    return bundle.classifier.predict(features)


def load_visual_knn_model(path: str | Path) -> VisualKnnModelBundle:
    model_path = Path(path)
    if not model_path.exists():
        raise ModelLoadError(f"Modelo visual não encontrado: {model_path}")
    try:
        classifier = VisualKnnClassifier.load(model_path)
    except Exception as exc:
        raise ModelLoadError(f"Falha ao carregar modelo visual: {model_path}") from exc
    return VisualKnnModelBundle(
        classifier=classifier,
        metadata=classifier.metadata_dict(),
    )


def predict_with_visual_knn(image: np.ndarray, bundle: VisualKnnModelBundle) -> BaselinePrediction:
    return bundle.classifier.predict_image(image)


def load_visual_svm_model(path: str | Path) -> VisualSvmModelBundle:
    model_path = Path(path)
    if not model_path.exists():
        raise ModelLoadError(f"Modelo visual SVM não encontrado: {model_path}")
    try:
        classifier = VisualSvmClassifier.load(model_path)
    except Exception as exc:
        raise ModelLoadError(f"Falha ao carregar modelo visual SVM: {model_path}") from exc
    return VisualSvmModelBundle(
        classifier=classifier,
        metadata=classifier.metadata_dict(),
    )


def predict_with_visual_svm(image: np.ndarray, bundle: VisualSvmModelBundle) -> BaselinePrediction:
    return bundle.classifier.predict_image(image)


def load_keras_model(path: str | Path, *, class_names_path: str | Path, threshold: float) -> KerasModelBundle:
    model_path = Path(path)
    names_path = Path(class_names_path)
    if not model_path.exists():
        raise ModelLoadError(f"Modelo final não encontrado: {model_path}")
    if not names_path.exists():
        raise ModelLoadError(f"Arquivo de classes não encontrado: {names_path}")
    try:
        import tensorflow as tf  # type: ignore
    except ImportError as exc:
        raise ModelLoadError("TensorFlow não está instalado para carregar o modelo final.") from exc
    try:
        model = tf.keras.models.load_model(model_path)
        class_names = json.loads(names_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ModelLoadError(f"Falha ao carregar modelo final: {model_path}") from exc
    return KerasModelBundle(
        model=model,
        class_names=list(class_names),
        threshold=threshold,
    )


def predict_with_keras(image: np.ndarray, bundle: KerasModelBundle, image_size: tuple[int, int]) -> BaselinePrediction:
    from ecoscan.image_processing.preprocessing import prepare_model_input

    prepared = prepare_model_input(image, image_size)
    probabilities_array = np.asarray(bundle.model.predict(prepared.model_input, verbose=0)[0], dtype=np.float32)
    best_index = int(np.argmax(probabilities_array))
    probability = float(probabilities_array[best_index])
    top_class = bundle.class_names[best_index]
    accepted = probability >= bundle.threshold
    probabilities = {
        class_id: float(probabilities_array[index])
        for index, class_id in enumerate(bundle.class_names)
    }
    return BaselinePrediction(
        top_class_id=top_class,
        class_id=top_class if accepted else None,
        probability=probability,
        probabilities=probabilities,
        accepted=accepted,
        threshold=bundle.threshold,
    )
