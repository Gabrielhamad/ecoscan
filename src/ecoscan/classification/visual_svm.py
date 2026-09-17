from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ecoscan.classification.baseline import BaselinePrediction
from ecoscan.classification.visual_features import VisualFeatureConfig, extract_visual_features


@dataclass(frozen=True)
class VisualSvmMetadata:
    algorithm: str
    feature_config: VisualFeatureConfig
    threshold: float
    kernel: str
    c_value: float
    gamma: str | float
    class_weight: str | None
    train_count: int
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "feature_config": self.feature_config.to_dict(),
            "threshold": self.threshold,
            "kernel": self.kernel,
            "c_value": self.c_value,
            "gamma": self.gamma,
            "class_weight": self.class_weight,
            "train_count": self.train_count,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VisualSvmMetadata":
        return cls(
            algorithm=str(data.get("algorithm", "visual_svm")),
            feature_config=VisualFeatureConfig.from_dict(dict(data.get("feature_config", {}))),
            threshold=float(data.get("threshold", 0.10)),
            kernel=str(data.get("kernel", "rbf")),
            c_value=float(data.get("c_value", 3.0)),
            gamma=data.get("gamma", "scale"),
            class_weight=data.get("class_weight"),
            train_count=int(data.get("train_count", 0)),
            notes=[str(item) for item in data.get("notes", [])],
        )


class VisualSvmClassifier:
    """Classificador visual clássico para uso no MVP sem depender de TensorFlow."""

    def __init__(self, *, model: object, classes: list[str], metadata: VisualSvmMetadata) -> None:
        self.model = model
        self.classes = classes
        self.metadata = metadata

    @classmethod
    def fit(
        cls,
        raw_features: np.ndarray,
        labels: list[str],
        *,
        feature_config: VisualFeatureConfig,
        threshold: float = 0.10,
        c_value: float = 3.0,
        gamma: str | float = "scale",
        kernel: str = "rbf",
        class_weight: str | None = "balanced",
        notes: list[str] | None = None,
    ) -> "VisualSvmClassifier":
        if len(raw_features) != len(labels):
            raise ValueError("raw_features and labels must have the same length.")
        if len(set(labels)) < 2:
            raise ValueError("At least two classes are required to train a visual SVM.")

        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.svm import SVC

        model = make_pipeline(
            StandardScaler(),
            SVC(
                C=float(c_value),
                gamma=gamma,
                kernel=kernel,
                class_weight=class_weight,
                decision_function_shape="ovr",
                random_state=42,
            ),
        )
        model.fit(raw_features.astype(np.float32), labels)
        classes = [str(class_id) for class_id in getattr(model, "classes_", sorted(set(labels)))]
        metadata = VisualSvmMetadata(
            algorithm="visual_svm",
            feature_config=feature_config,
            threshold=float(threshold),
            kernel=kernel,
            c_value=float(c_value),
            gamma=gamma,
            class_weight=class_weight,
            train_count=len(labels),
            notes=notes or [],
        )
        return cls(model=model, classes=classes, metadata=metadata)

    def _prepare_feature(self, image: np.ndarray) -> np.ndarray:
        return extract_visual_features(image, self.metadata.feature_config)[None, :].astype(np.float32)

    @staticmethod
    def _softmax(scores: np.ndarray) -> np.ndarray:
        shifted = scores.astype(np.float64) - float(np.max(scores))
        exp = np.exp(np.clip(shifted, -60.0, 60.0))
        total = float(exp.sum()) or 1.0
        return (exp / total).astype(np.float32)

    def _predict_probabilities(self, feature: np.ndarray) -> dict[str, float]:
        if hasattr(self.model, "predict_proba"):
            probabilities = np.asarray(self.model.predict_proba(feature)[0], dtype=np.float32)  # type: ignore[attr-defined]
            model_classes = [str(class_id) for class_id in getattr(self.model, "classes_", self.classes)]
            return {
                class_id: float(probabilities[index])
                for index, class_id in enumerate(model_classes[: len(probabilities)])
            }

        if not hasattr(self.model, "decision_function"):
            prediction = str(self.model.predict(feature)[0])  # type: ignore[attr-defined]
            return {class_id: 1.0 if class_id == prediction else 0.0 for class_id in self.classes}

        raw_scores = np.asarray(self.model.decision_function(feature), dtype=np.float32)  # type: ignore[attr-defined]
        if raw_scores.ndim == 0 or raw_scores.reshape(-1).shape[0] == 1:
            margin = float(raw_scores.reshape(-1)[0])
            scores = np.asarray([-margin, margin], dtype=np.float32)
        else:
            scores = raw_scores.reshape(-1)

        probabilities = self._softmax(scores)
        return {
            class_id: float(probabilities[index])
            for index, class_id in enumerate(self.classes[: len(probabilities)])
        }

    def predict_image(self, image: np.ndarray) -> BaselinePrediction:
        return self.predict_feature(self._prepare_feature(image))

    def predict_feature(self, feature: np.ndarray) -> BaselinePrediction:
        probabilities = self._predict_probabilities(feature.astype(np.float32))
        top_class = max(probabilities, key=probabilities.get)
        probability = probabilities[top_class]
        accepted = probability >= self.metadata.threshold
        return BaselinePrediction(
            top_class_id=top_class,
            class_id=top_class if accepted else None,
            probability=probability,
            probabilities=probabilities,
            accepted=accepted,
            threshold=self.metadata.threshold,
        )

    def save(self, path: str | Path) -> Path:
        from joblib import dump

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dump(
            {
                "model_type": "visual_svm",
                "classes": self.classes,
                "model": self.model,
                "metadata": self.metadata.to_dict(),
            },
            output_path,
        )
        return output_path

    @classmethod
    def load(cls, path: str | Path) -> "VisualSvmClassifier":
        from joblib import load

        payload = load(Path(path))
        metadata = VisualSvmMetadata.from_dict(dict(payload.get("metadata", {})))
        classes = [str(class_id) for class_id in payload.get("classes", [])]
        model = payload["model"]
        if not classes:
            classes = [str(class_id) for class_id in getattr(model, "classes_", [])]
        return cls(model=model, classes=classes, metadata=metadata)

    def metadata_dict(self) -> dict[str, Any]:
        return self.metadata.to_dict()
