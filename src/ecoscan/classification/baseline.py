from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class BaselinePrediction:
    top_class_id: str
    class_id: str | None
    probability: float
    probabilities: dict[str, float]
    accepted: bool
    threshold: float


class NearestCentroidClassifier:
    def __init__(
        self,
        *,
        classes: list[str],
        centroids: np.ndarray,
        threshold: float,
        softmax_temperature: float = 1.0,
    ) -> None:
        self.classes = classes
        self.centroids = centroids.astype(np.float32)
        self.threshold = float(threshold)
        self.softmax_temperature = max(float(softmax_temperature), 1e-6)

    @classmethod
    def fit(
        cls,
        features: np.ndarray,
        labels: list[str],
        *,
        threshold: float,
        softmax_temperature: float = 1.0,
    ) -> "NearestCentroidClassifier":
        classes = sorted(set(labels))
        if not classes:
            raise ValueError("Cannot fit baseline without labels.")
        centroids = []
        for class_id in classes:
            class_features = features[np.array(labels) == class_id]
            centroids.append(class_features.mean(axis=0))
        return cls(
            classes=classes,
            centroids=np.vstack(centroids),
            threshold=threshold,
            softmax_temperature=softmax_temperature,
        )

    def predict(self, feature: np.ndarray) -> BaselinePrediction:
        distances = np.linalg.norm(self.centroids - feature.astype(np.float32), axis=1)
        scores = -distances / self.softmax_temperature
        scores = scores - scores.max()
        exp_scores = np.exp(scores)
        probabilities_array = exp_scores / exp_scores.sum()
        best_index = int(np.argmax(probabilities_array))
        probability = float(probabilities_array[best_index])
        accepted = probability >= self.threshold
        probabilities = {
            class_id: float(probabilities_array[index])
            for index, class_id in enumerate(self.classes)
        }
        return BaselinePrediction(
            top_class_id=self.classes[best_index],
            class_id=self.classes[best_index] if accepted else None,
            probability=probability,
            probabilities=probabilities,
            accepted=accepted,
            threshold=self.threshold,
        )

    def save(self, path: str | Path, metadata: dict) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output = {
            "type": "nearest_centroid_baseline",
            "classes": self.classes,
            "centroids": self.centroids.tolist(),
            "threshold": self.threshold,
            "softmax_temperature": self.softmax_temperature,
            "metadata": metadata,
        }
        output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    @classmethod
    def load(cls, path: str | Path) -> "NearestCentroidClassifier":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            classes=list(data["classes"]),
            centroids=np.asarray(data["centroids"], dtype=np.float32),
            threshold=float(data["threshold"]),
            softmax_temperature=float(data.get("softmax_temperature", 1.0)),
        )


class KNearestNeighborsClassifier:
    def __init__(
        self,
        *,
        classes: list[str],
        features: np.ndarray,
        labels: list[str],
        threshold: float,
        k_neighbors: int = 5,
    ) -> None:
        if len(features) != len(labels):
            raise ValueError("features and labels must have the same length.")
        self.classes = classes
        self.features = features.astype(np.float32)
        self.labels = labels
        self.threshold = float(threshold)
        self.k_neighbors = max(1, int(k_neighbors))

    @classmethod
    def fit(
        cls,
        features: np.ndarray,
        labels: list[str],
        *,
        threshold: float,
        k_neighbors: int = 5,
    ) -> "KNearestNeighborsClassifier":
        classes = sorted(set(labels))
        if not classes:
            raise ValueError("Cannot fit baseline without labels.")
        return cls(
            classes=classes,
            features=features,
            labels=labels,
            threshold=threshold,
            k_neighbors=k_neighbors,
        )

    def predict(self, feature: np.ndarray) -> BaselinePrediction:
        distances = np.linalg.norm(self.features - feature.astype(np.float32), axis=1)
        neighbor_count = min(self.k_neighbors, len(distances))
        nearest_indices = np.argsort(distances)[:neighbor_count]

        scores = {class_id: 0.0 for class_id in self.classes}
        for index in nearest_indices:
            label = self.labels[int(index)]
            scores[label] += 1.0 / (float(distances[int(index)]) + 1e-6)

        total_score = sum(scores.values()) or 1.0
        probabilities = {
            class_id: score / total_score
            for class_id, score in scores.items()
        }
        top_class = max(probabilities, key=probabilities.get)
        probability = float(probabilities[top_class])
        accepted = probability >= self.threshold
        return BaselinePrediction(
            top_class_id=top_class,
            class_id=top_class if accepted else None,
            probability=probability,
            probabilities=probabilities,
            accepted=accepted,
            threshold=self.threshold,
        )

    def save(self, path: str | Path, metadata: dict) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output = {
            "type": "knn_baseline",
            "classes": self.classes,
            "features": self.features.tolist(),
            "labels": self.labels,
            "threshold": self.threshold,
            "k_neighbors": self.k_neighbors,
            "metadata": metadata,
        }
        output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    @classmethod
    def load(cls, path: str | Path) -> "KNearestNeighborsClassifier":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            classes=list(data["classes"]),
            features=np.asarray(data["features"], dtype=np.float32),
            labels=list(data["labels"]),
            threshold=float(data["threshold"]),
            k_neighbors=int(data.get("k_neighbors", 5)),
        )
