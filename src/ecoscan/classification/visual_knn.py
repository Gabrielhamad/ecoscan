from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ecoscan.classification.baseline import BaselinePrediction
from ecoscan.classification.visual_features import VisualFeatureConfig, extract_visual_features


@dataclass(frozen=True)
class VisualKnnMetadata:
    algorithm: str
    feature_config: VisualFeatureConfig
    threshold: float
    k_neighbors: int
    distance_metric: str
    score_mode: str
    train_count: int
    notes: list[str]

    def to_json(self) -> str:
        return json.dumps(
            {
                "algorithm": self.algorithm,
                "feature_config": self.feature_config.to_dict(),
                "threshold": self.threshold,
                "k_neighbors": self.k_neighbors,
                "distance_metric": self.distance_metric,
                "score_mode": self.score_mode,
                "train_count": self.train_count,
                "notes": self.notes,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> "VisualKnnMetadata":
        data = json.loads(value.decode("utf-8") if isinstance(value, bytes) else value)
        return cls(
            algorithm=str(data.get("algorithm", "visual_knn")),
            feature_config=VisualFeatureConfig.from_dict(dict(data.get("feature_config", {}))),
            threshold=float(data.get("threshold", 0.0)),
            k_neighbors=int(data.get("k_neighbors", 5)),
            distance_metric=str(data.get("distance_metric", "cosine")),
            score_mode=str(data.get("score_mode", "neighbor_vote")),
            train_count=int(data.get("train_count", 0)),
            notes=[str(item) for item in data.get("notes", [])],
        )


class VisualKnnClassifier:
    def __init__(
        self,
        *,
        classes: list[str],
        features: np.ndarray,
        labels: list[str],
        feature_mean: np.ndarray,
        feature_std: np.ndarray,
        metadata: VisualKnnMetadata,
    ) -> None:
        if len(features) != len(labels):
            raise ValueError("features and labels must have the same length.")
        self.classes = classes
        self.features = features.astype(np.float32)
        self.labels = labels
        self.feature_mean = feature_mean.astype(np.float32)
        self.feature_std = np.where(feature_std.astype(np.float32) < 1e-6, 1.0, feature_std.astype(np.float32))
        self.metadata = metadata
        if self.metadata.distance_metric == "cosine":
            norms = np.linalg.norm(self.features, axis=1, keepdims=True)
            self._normalized_features = self.features / (norms + 1e-9)
        else:
            self._normalized_features = self.features
        self._class_indices = {
            class_id: np.asarray(
                [index for index, label in enumerate(self.labels) if label == class_id],
                dtype=np.int32,
            )
            for class_id in self.classes
        }

    @classmethod
    def fit(
        cls,
        raw_features: np.ndarray,
        labels: list[str],
        *,
        classes: list[str],
        feature_config: VisualFeatureConfig,
        threshold: float,
        k_neighbors: int,
        distance_metric: str,
        score_mode: str = "neighbor_vote",
        notes: list[str] | None = None,
    ) -> "VisualKnnClassifier":
        feature_mean = raw_features.mean(axis=0)
        feature_std = raw_features.std(axis=0)
        normalized = cls.normalize_features(raw_features, feature_mean, feature_std)
        metadata = VisualKnnMetadata(
            algorithm="visual_knn",
            feature_config=feature_config,
            threshold=float(threshold),
            k_neighbors=max(1, int(k_neighbors)),
            distance_metric=distance_metric,
            score_mode=score_mode,
            train_count=len(labels),
            notes=notes or [],
        )
        return cls(
            classes=classes,
            features=normalized,
            labels=labels,
            feature_mean=feature_mean,
            feature_std=feature_std,
            metadata=metadata,
        )

    @staticmethod
    def normalize_features(raw_features: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
        safe_std = np.where(std.astype(np.float32) < 1e-6, 1.0, std.astype(np.float32))
        return ((raw_features.astype(np.float32) - mean.astype(np.float32)) / safe_std).astype(np.float32)

    def _prepare_feature(self, image: np.ndarray) -> np.ndarray:
        raw = extract_visual_features(image, self.metadata.feature_config)
        return self.normalize_features(raw[None, :], self.feature_mean, self.feature_std)[0]

    def predict_image(self, image: np.ndarray) -> BaselinePrediction:
        return self.predict_feature(self._prepare_feature(image))

    def predict_feature(self, feature: np.ndarray) -> BaselinePrediction:
        if self.metadata.score_mode == "class_balanced":
            return self._predict_feature_class_balanced(feature)
        return self._predict_feature_neighbor_vote(feature)

    def _predict_feature_neighbor_vote(self, feature: np.ndarray) -> BaselinePrediction:
        neighbor_count = min(self.metadata.k_neighbors, len(self.features))
        if self.metadata.distance_metric == "cosine":
            normalized = feature.astype(np.float32)
            normalized = normalized / (float(np.linalg.norm(normalized)) + 1e-9)
            similarities = self._normalized_features @ normalized
            nearest_indices = np.argsort(-similarities)[:neighbor_count]
            raw_weights = np.maximum(similarities[nearest_indices] + 1.0, 1e-6)
        else:
            distances = np.linalg.norm(self.features - feature.astype(np.float32), axis=1)
            nearest_indices = np.argsort(distances)[:neighbor_count]
            raw_weights = 1.0 / (distances[nearest_indices] + 1e-6)

        scores = {class_id: 0.0 for class_id in self.classes}
        for index, weight in zip(nearest_indices, raw_weights, strict=True):
            scores[self.labels[int(index)]] += float(weight)

        total_score = sum(scores.values()) or 1.0
        probabilities = {
            class_id: float(score / total_score)
            for class_id, score in scores.items()
        }
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

    def _predict_feature_class_balanced(self, feature: np.ndarray) -> BaselinePrediction:
        scores = {class_id: 0.0 for class_id in self.classes}
        for class_id, indices in self._class_indices.items():
            if len(indices) == 0:
                continue
            class_features = self.features[indices]
            neighbor_count = min(self.metadata.k_neighbors, len(class_features))
            if self.metadata.distance_metric == "cosine":
                normalized = feature.astype(np.float32)
                normalized = normalized / (float(np.linalg.norm(normalized)) + 1e-9)
                class_normalized = self._normalized_features[indices]
                similarities = class_normalized @ normalized
                top_values = np.sort(similarities)[-neighbor_count:]
                weights = np.maximum(top_values + 1.0, 1e-6)
            else:
                distances = np.linalg.norm(class_features - feature.astype(np.float32), axis=1)
                top_values = np.sort(distances)[:neighbor_count]
                weights = 1.0 / (top_values + 1e-6)
            scores[class_id] = float(np.mean(weights))

        total_score = sum(scores.values()) or 1.0
        probabilities = {
            class_id: float(score / total_score)
            for class_id, score in scores.items()
        }
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
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            output_path,
            model_type=np.asarray("visual_knn"),
            classes=np.asarray(self.classes, dtype=object),
            labels=np.asarray(self.labels, dtype=object),
            features=self.features.astype(np.float32),
            feature_mean=self.feature_mean.astype(np.float32),
            feature_std=self.feature_std.astype(np.float32),
            metadata=np.asarray(self.metadata.to_json()),
        )
        return output_path

    @classmethod
    def load(cls, path: str | Path) -> "VisualKnnClassifier":
        with np.load(Path(path), allow_pickle=True) as payload:
            metadata = VisualKnnMetadata.from_json(str(payload["metadata"].item()))
            return cls(
                classes=[str(item) for item in payload["classes"].tolist()],
                labels=[str(item) for item in payload["labels"].tolist()],
                features=np.asarray(payload["features"], dtype=np.float32),
                feature_mean=np.asarray(payload["feature_mean"], dtype=np.float32),
                feature_std=np.asarray(payload["feature_std"], dtype=np.float32),
                metadata=metadata,
            )

    def metadata_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.metadata.algorithm,
            "feature_config": self.metadata.feature_config.to_dict(),
            "threshold": self.metadata.threshold,
            "k_neighbors": self.metadata.k_neighbors,
            "distance_metric": self.metadata.distance_metric,
            "score_mode": self.metadata.score_mode,
            "train_count": self.metadata.train_count,
            "notes": list(self.metadata.notes),
        }
