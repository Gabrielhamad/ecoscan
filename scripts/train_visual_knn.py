from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from ecoscan.classification.visual_features import VisualFeatureConfig, extract_visual_features
from ecoscan.classification.visual_knn import VisualKnnClassifier
from ecoscan.config import load_config
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.metrics.classification_metrics import classification_report
from train_baseline import _iter_split_images


@dataclass(frozen=True)
class VisualCandidate:
    feature_config: VisualFeatureConfig
    k_neighbors: int
    distance_metric: str
    threshold: float
    score_mode: str


def _load_visual_features(
    items: list[tuple[Path, str]],
    feature_config: VisualFeatureConfig,
    *,
    min_size: tuple[int, int],
    extensions: frozenset[str],
) -> tuple[np.ndarray, list[str], list[str]]:
    features = []
    labels = []
    paths = []
    for path, label in items:
        loaded = load_rgb_image(path, allowed_extensions=extensions, min_size=min_size)
        features.append(extract_visual_features(loaded.array, feature_config))
        labels.append(label)
        paths.append(path.as_posix())
    if not features:
        return np.empty((0, 0), dtype=np.float32), labels, paths
    return np.vstack(features).astype(np.float32), labels, paths


def _predict_many(classifier: VisualKnnClassifier, features: np.ndarray) -> tuple[list[str], list[str | None], list[float]]:
    raw_predictions: list[str] = []
    accepted_predictions: list[str | None] = []
    probabilities: list[float] = []
    for feature in features:
        prediction = classifier.predict_feature(feature)
        raw_predictions.append(prediction.top_class_id)
        accepted_predictions.append(prediction.class_id)
        probabilities.append(prediction.probability)
    return raw_predictions, accepted_predictions, probabilities


def _write_predictions(
    path: Path,
    labels: list[str],
    raw_predictions: list[str],
    accepted_predictions: list[str | None],
    probabilities: list[float],
    paths: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["path", "true_label", "raw_predicted_label", "accepted_predicted_label", "probability"],
        )
        writer.writeheader()
        for source_path, label, raw_prediction, accepted_prediction, probability in zip(
            paths,
            labels,
            raw_predictions,
            accepted_predictions,
            probabilities,
            strict=True,
        ):
            writer.writerow(
                {
                    "path": source_path,
                    "true_label": label,
                    "raw_predicted_label": raw_prediction,
                    "accepted_predicted_label": accepted_prediction or "__uncertain__",
                    "probability": f"{probability:.6f}",
                }
            )


def _score(labels: list[str], raw_predictions: list[str], probabilities: list[float], threshold: float) -> dict:
    total = max(1, len(labels))
    accepted_indexes = [
        index
        for index, probability in enumerate(probabilities)
        if probability >= threshold
    ]
    raw_correct = sum(label == prediction for label, prediction in zip(labels, raw_predictions, strict=True))
    accepted_correct = sum(labels[index] == raw_predictions[index] for index in accepted_indexes)
    accepted_count = len(accepted_indexes)
    coverage = accepted_count / total
    accepted_precision = accepted_correct / accepted_count if accepted_count else 0.0
    rejected_aware_accuracy = accepted_correct / total
    deployment_score = (
        0.50 * rejected_aware_accuracy
        + 0.30 * accepted_precision
        + 0.20 * coverage
    )
    return {
        "raw_accuracy": raw_correct / total,
        "coverage": coverage,
        "accepted_precision": accepted_precision,
        "rejected_aware_accuracy": rejected_aware_accuracy,
        "accepted_count": accepted_count,
        "uncertain_count": len(labels) - accepted_count,
        "deployment_score": deployment_score,
    }


def _candidate_row(candidate: VisualCandidate, split_name: str, metrics: dict) -> dict:
    return {
        "image_size": f"{candidate.feature_config.image_size[0]}x{candidate.feature_config.image_size[1]}",
        "rgb_bins": candidate.feature_config.rgb_histogram_bins,
        "hsv_bins": candidate.feature_config.hsv_histogram_bins,
        "k_neighbors": candidate.k_neighbors,
        "distance_metric": candidate.distance_metric,
        "score_mode": candidate.score_mode,
        "threshold": candidate.threshold,
        "split": split_name,
        **metrics,
    }


def _build_candidates() -> list[VisualCandidate]:
    feature_configs = [
        VisualFeatureConfig(image_size=(96, 96), rgb_histogram_bins=12, hsv_histogram_bins=10),
        VisualFeatureConfig(image_size=(128, 128), rgb_histogram_bins=16, hsv_histogram_bins=12),
    ]
    thresholds = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    candidates: list[VisualCandidate] = []
    for feature_config in feature_configs:
        for distance_metric in ["cosine", "euclidean"]:
            for k_neighbors in [1, 3, 5, 7, 9, 11, 15]:
                for threshold in thresholds:
                    for score_mode in ["neighbor_vote", "class_balanced"]:
                        candidates.append(
                            VisualCandidate(
                                feature_config=feature_config,
                                k_neighbors=k_neighbors,
                                distance_metric=distance_metric,
                                threshold=threshold,
                                score_mode=score_mode,
                            )
                        )
    return candidates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the EcoScan visual KNN classifier.")
    parser.add_argument("--output-model", type=Path, default=PROJECT_ROOT / "models" / "vision_classifier.npz")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "visual_training")
    parser.add_argument("--source", type=Path, default=None, help="Optional split root. Defaults to configured train/validation/test.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    classes = list(config.classes)
    train_items = _iter_split_images(config.directories["train_data"], classes, config.allowed_extensions)
    validation_items = _iter_split_images(config.directories["validation_data"], classes, config.allowed_extensions)
    test_items = _iter_split_images(config.directories["test_data"], classes, config.allowed_extensions)
    if not train_items:
        print("No training images found. Run scripts\\split_dataset.py --source data\\processed --overwrite first.")
        return 1

    args.report_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    summaries: list[dict] = []

    grouped: dict[tuple, list[VisualCandidate]] = {}
    for candidate in _build_candidates():
        key = (json.dumps(candidate.feature_config.to_dict(), sort_keys=True),)
        grouped.setdefault(key, []).append(candidate)

    for candidates in grouped.values():
        feature_config = candidates[0].feature_config
        train_raw_features, train_labels, _ = _load_visual_features(
            train_items,
            feature_config,
            min_size=config.min_image_size,
            extensions=config.allowed_extensions,
        )
        validation_raw_features, validation_labels, validation_paths = _load_visual_features(
            validation_items,
            feature_config,
            min_size=config.min_image_size,
            extensions=config.allowed_extensions,
        )
        test_raw_features, test_labels, test_paths = _load_visual_features(
            test_items,
            feature_config,
            min_size=config.min_image_size,
            extensions=config.allowed_extensions,
        )

        cache: dict[tuple[int, str, str], dict[str, object]] = {}
        for candidate in candidates:
            cache_key = (candidate.k_neighbors, candidate.distance_metric, candidate.score_mode)
            if cache_key not in cache:
                classifier = VisualKnnClassifier.fit(
                    train_raw_features,
                    train_labels,
                    classes=classes,
                    feature_config=feature_config,
                    threshold=0.0,
                    k_neighbors=candidate.k_neighbors,
                    distance_metric=candidate.distance_metric,
                    score_mode=candidate.score_mode,
                    notes=[],
                )
                validation_features = classifier.normalize_features(
                    validation_raw_features,
                    classifier.feature_mean,
                    classifier.feature_std,
                )
                test_features = classifier.normalize_features(
                    test_raw_features,
                    classifier.feature_mean,
                    classifier.feature_std,
                )
                validation_raw_predictions, _, validation_probabilities = _predict_many(classifier, validation_features)
                test_raw_predictions, _, test_probabilities = _predict_many(classifier, test_features)
                cache[cache_key] = {
                    "classifier": classifier,
                    "validation_features": validation_features,
                    "test_features": test_features,
                    "validation_raw_predictions": validation_raw_predictions,
                    "validation_probabilities": validation_probabilities,
                    "test_raw_predictions": test_raw_predictions,
                    "test_probabilities": test_probabilities,
                }

            cached = cache[cache_key]
            validation_metrics = _score(
                validation_labels,
                cached["validation_raw_predictions"],  # type: ignore[arg-type]
                cached["validation_probabilities"],  # type: ignore[arg-type]
                candidate.threshold,
            )
            test_metrics = _score(
                test_labels,
                cached["test_raw_predictions"],  # type: ignore[arg-type]
                cached["test_probabilities"],  # type: ignore[arg-type]
                candidate.threshold,
            )
            rows.append(_candidate_row(candidate, "validation", validation_metrics))
            rows.append(_candidate_row(candidate, "test", test_metrics))
            summaries.append(
                {
                    "candidate": candidate,
                    "validation": validation_metrics,
                    "test": test_metrics,
                    "cache_key": cache_key,
                    "feature_key": json.dumps(candidate.feature_config.to_dict(), sort_keys=True),
                }
            )

    eligible = [item for item in summaries if item["validation"]["coverage"] >= 0.55]
    ranked = sorted(
        eligible or summaries,
        key=lambda item: (
            item["validation"]["deployment_score"],
            item["validation"]["raw_accuracy"],
            item["validation"]["coverage"],
        ),
        reverse=True,
    )
    recommended = ranked[0]
    candidate: VisualCandidate = recommended["candidate"]

    train_raw_features, train_labels, _ = _load_visual_features(
        train_items,
        candidate.feature_config,
        min_size=config.min_image_size,
        extensions=config.allowed_extensions,
    )
    classifier = VisualKnnClassifier.fit(
        train_raw_features,
        train_labels,
        classes=classes,
        feature_config=candidate.feature_config,
        threshold=candidate.threshold,
        k_neighbors=candidate.k_neighbors,
        distance_metric=candidate.distance_metric,
        score_mode=candidate.score_mode,
        notes=[
            "Modelo visual clássico treinado sobre imagens processadas por filtragem e segmentação.",
            "Usa descritores de cor RGB/HSV, HOG para forma e LBP para textura.",
            "Não substitui transfer learning após curadoria completa, mas melhora o baseline simples.",
        ],
    )
    model_path = classifier.save(args.output_model)

    with (args.report_dir / "visual_tuning.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    def _serialize(item: dict) -> dict:
        item_candidate: VisualCandidate = item["candidate"]
        return {
            "candidate": {
                "feature_config": item_candidate.feature_config.to_dict(),
                "k_neighbors": item_candidate.k_neighbors,
                "distance_metric": item_candidate.distance_metric,
                "score_mode": item_candidate.score_mode,
                "threshold": item_candidate.threshold,
            },
            "validation": item["validation"],
            "test": item["test"],
        }

    summary = {
        "model_path": str(model_path),
        "recommendation_note": (
            "Modelo visual clássico para melhorar o MVP sem dependências pesadas. "
            "A precisão final ainda depende de curadoria e de mais imagens representativas."
        ),
        "recommended": _serialize(recommended),
        "top_candidates": [_serialize(item) for item in ranked[:12]],
    }
    (args.report_dir / "visual_training_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    validation_raw_features, validation_labels, validation_paths = _load_visual_features(
        validation_items,
        candidate.feature_config,
        min_size=config.min_image_size,
        extensions=config.allowed_extensions,
    )
    test_raw_features, test_labels, test_paths = _load_visual_features(
        test_items,
        candidate.feature_config,
        min_size=config.min_image_size,
        extensions=config.allowed_extensions,
    )
    for split_name, split_features, split_labels, split_paths in [
        ("validation", validation_raw_features, validation_labels, validation_paths),
        ("test", test_raw_features, test_labels, test_paths),
    ]:
        normalized_features = classifier.normalize_features(
            split_features,
            classifier.feature_mean,
            classifier.feature_std,
        )
        raw_predictions, accepted_predictions, probabilities = _predict_many(classifier, normalized_features)
        report = {
            "raw_top1": classification_report(split_labels, raw_predictions, classes),
            "with_rejection": classification_report(split_labels, accepted_predictions, classes),
        }
        (args.report_dir / f"{split_name}_metrics.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        _write_predictions(
            args.report_dir / f"{split_name}_predictions.csv",
            split_labels,
            raw_predictions,
            accepted_predictions,
            probabilities,
            split_paths,
        )

    print("EcoScan visual KNN trained.")
    print(f"Model: {model_path}")
    print(
        "Recommended: "
        f"size={candidate.feature_config.image_size[0]}x{candidate.feature_config.image_size[1]}, "
        f"k={candidate.k_neighbors}, metric={candidate.distance_metric}, "
        f"mode={candidate.score_mode}, threshold={candidate.threshold}"
    )
    print(
        "validation: "
        f"raw_accuracy={recommended['validation']['raw_accuracy']:.3f}, "
        f"coverage={recommended['validation']['coverage']:.3f}, "
        f"accepted_precision={recommended['validation']['accepted_precision']:.3f}"
    )
    print(
        "test: "
        f"raw_accuracy={recommended['test']['raw_accuracy']:.3f}, "
        f"coverage={recommended['test']['coverage']:.3f}, "
        f"accepted_precision={recommended['test']['accepted_precision']:.3f}"
    )
    print(f"Report: {args.report_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
