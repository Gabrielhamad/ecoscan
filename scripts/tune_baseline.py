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

from ecoscan.classification.baseline import KNearestNeighborsClassifier, NearestCentroidClassifier
from ecoscan.classification.features import FeatureConfig
from ecoscan.config import load_config
from train_baseline import _iter_split_images, _load_features


@dataclass(frozen=True)
class Candidate:
    algorithm: str
    image_size: tuple[int, int]
    histogram_bins: int
    confidence_threshold: float
    k_neighbors: int | None = None
    softmax_temperature: float | None = None


def _predict_many(classifier, features: np.ndarray) -> tuple[list[str], list[float]]:
    raw_predictions: list[str] = []
    probabilities: list[float] = []
    for feature in features:
        prediction = classifier.predict(feature)
        raw_predictions.append(prediction.top_class_id)
        probabilities.append(prediction.probability)
    return raw_predictions, probabilities


def _score(labels: list[str], raw_predictions: list[str], probabilities: list[float], threshold: float) -> dict:
    total = max(1, len(labels))
    accepted_indexes = [
        index
        for index, probability in enumerate(probabilities)
        if probability >= threshold
    ]
    raw_correct = sum(
        label == predicted
        for label, predicted in zip(labels, raw_predictions, strict=True)
    )
    accepted_correct = sum(
        labels[index] == raw_predictions[index]
        for index in accepted_indexes
    )
    accepted_count = len(accepted_indexes)
    coverage = accepted_count / total
    raw_accuracy = raw_correct / total
    accepted_precision = accepted_correct / accepted_count if accepted_count else 0.0
    rejected_aware_accuracy = accepted_correct / total

    # The score favors useful coverage but still rewards only accepted correct predictions.
    deployment_score = (
        0.45 * rejected_aware_accuracy
        + 0.35 * accepted_precision
        + 0.20 * coverage
    )
    return {
        "raw_accuracy": raw_accuracy,
        "coverage": coverage,
        "accepted_precision": accepted_precision,
        "rejected_aware_accuracy": rejected_aware_accuracy,
        "accepted_count": accepted_count,
        "uncertain_count": len(labels) - accepted_count,
        "deployment_score": deployment_score,
    }


def _candidate_row(candidate: Candidate, split: str, metrics: dict) -> dict:
    return {
        "algorithm": candidate.algorithm,
        "image_size": f"{candidate.image_size[0]}x{candidate.image_size[1]}",
        "histogram_bins": candidate.histogram_bins,
        "confidence_threshold": candidate.confidence_threshold,
        "k_neighbors": candidate.k_neighbors or "",
        "softmax_temperature": candidate.softmax_temperature or "",
        "split": split,
        **metrics,
    }


def _build_candidates() -> list[Candidate]:
    thresholds = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60]
    feature_sets = [
        ((96, 96), 8),
        ((128, 128), 8),
        ((96, 96), 12),
        ((128, 128), 12),
    ]
    candidates: list[Candidate] = []
    for image_size, histogram_bins in feature_sets:
        for k_neighbors in [1, 3, 5, 7, 9]:
            for threshold in thresholds:
                candidates.append(
                    Candidate(
                        algorithm="knn",
                        image_size=image_size,
                        histogram_bins=histogram_bins,
                        confidence_threshold=threshold,
                        k_neighbors=k_neighbors,
                    )
                )
        for temperature in [0.05, 0.10, 0.20, 0.50, 1.00]:
            for threshold in thresholds:
                candidates.append(
                    Candidate(
                        algorithm="nearest_centroid",
                        image_size=image_size,
                        histogram_bins=histogram_bins,
                        confidence_threshold=threshold,
                        softmax_temperature=temperature,
                    )
                )
    return candidates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tune EcoScan baseline classifier settings.")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports" / "baseline_tuning")
    parser.add_argument("--top", type=int, default=12)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    classes = list(config.classes)
    train_items = _iter_split_images(config.directories["train_data"], classes, config.allowed_extensions)
    validation_items = _iter_split_images(config.directories["validation_data"], classes, config.allowed_extensions)
    test_items = _iter_split_images(config.directories["test_data"], classes, config.allowed_extensions)
    if not train_items or not validation_items or not test_items:
        print("Missing split images. Run scripts\\split_dataset.py --source data\\processed --overwrite first.")
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    summary: list[dict] = []

    grouped_candidates: dict[tuple[tuple[int, int], int], list[Candidate]] = {}
    for candidate in _build_candidates():
        grouped_candidates.setdefault((candidate.image_size, candidate.histogram_bins), []).append(candidate)

    for (image_size, histogram_bins), candidates in grouped_candidates.items():
        feature_config = FeatureConfig(image_size=image_size, histogram_bins=histogram_bins)
        train_features, train_labels, _ = _load_features(
            train_items,
            feature_config,
            config.min_image_size,
            config.allowed_extensions,
        )
        validation_features, validation_labels, _ = _load_features(
            validation_items,
            feature_config,
            config.min_image_size,
            config.allowed_extensions,
        )
        test_features, test_labels, _ = _load_features(
            test_items,
            feature_config,
            config.min_image_size,
            config.allowed_extensions,
        )

        prediction_cache: dict[tuple, tuple[list[str], list[float], list[str], list[float]]] = {}
        for candidate in candidates:
            cache_key = (
                candidate.algorithm,
                candidate.k_neighbors,
                candidate.softmax_temperature,
            )
            if cache_key not in prediction_cache:
                if candidate.algorithm == "knn":
                    classifier = KNearestNeighborsClassifier.fit(
                        train_features,
                        train_labels,
                        threshold=0.0,
                        k_neighbors=int(candidate.k_neighbors or 5),
                    )
                else:
                    classifier = NearestCentroidClassifier.fit(
                        train_features,
                        train_labels,
                        threshold=0.0,
                        softmax_temperature=float(candidate.softmax_temperature or 1.0),
                    )
                validation_predictions, validation_probabilities = _predict_many(classifier, validation_features)
                test_predictions, test_probabilities = _predict_many(classifier, test_features)
                prediction_cache[cache_key] = (
                    validation_predictions,
                    validation_probabilities,
                    test_predictions,
                    test_probabilities,
                )

            validation_predictions, validation_probabilities, test_predictions, test_probabilities = prediction_cache[cache_key]
            validation_metrics = _score(
                validation_labels,
                validation_predictions,
                validation_probabilities,
                candidate.confidence_threshold,
            )
            test_metrics = _score(
                test_labels,
                test_predictions,
                test_probabilities,
                candidate.confidence_threshold,
            )
            rows.append(_candidate_row(candidate, "validation", validation_metrics))
            rows.append(_candidate_row(candidate, "test", test_metrics))
            summary.append(
                {
                    "candidate": candidate,
                    "validation": validation_metrics,
                    "test": test_metrics,
                }
            )

    sorted_summary = sorted(
        summary,
        key=lambda item: (
            item["validation"]["deployment_score"],
            item["validation"]["rejected_aware_accuracy"],
            item["validation"]["coverage"],
            item["candidate"].k_neighbors or 0,
        ),
        reverse=True,
    )
    recommended = sorted_summary[0]
    top_items = sorted_summary[: max(1, args.top)]

    fieldnames = list(rows[0].keys()) if rows else []
    with (args.output_dir / "baseline_tuning.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    def _serialize(item: dict) -> dict:
        candidate: Candidate = item["candidate"]
        return {
            "candidate": {
                "algorithm": candidate.algorithm,
                "image_size": list(candidate.image_size),
                "histogram_bins": candidate.histogram_bins,
                "confidence_threshold": candidate.confidence_threshold,
                "k_neighbors": candidate.k_neighbors,
                "softmax_temperature": candidate.softmax_temperature,
            },
            "validation": item["validation"],
            "test": item["test"],
        }

    report = {
        "recommendation_note": (
            "Use this as a baseline calibration only. With a small and web-sourced dataset, "
            "manual curation and more images are still required before claiming production accuracy."
        ),
        "recommended": _serialize(recommended),
        "top_candidates": [_serialize(item) for item in top_items],
    }
    (args.output_dir / "baseline_tuning_summary.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    candidate = recommended["candidate"]
    validation = recommended["validation"]
    test = recommended["test"]
    print("EcoScan baseline tuning complete.")
    print(
        "Recommended: "
        f"algorithm={candidate.algorithm}, image_size={candidate.image_size[0]}x{candidate.image_size[1]}, "
        f"bins={candidate.histogram_bins}, threshold={candidate.confidence_threshold}, "
        f"k={candidate.k_neighbors or '-'}, temp={candidate.softmax_temperature or '-'}"
    )
    print(
        "validation: "
        f"coverage={validation['coverage']:.3f}, accepted_precision={validation['accepted_precision']:.3f}, "
        f"rejected_aware_accuracy={validation['rejected_aware_accuracy']:.3f}, raw_accuracy={validation['raw_accuracy']:.3f}"
    )
    print(
        "test: "
        f"coverage={test['coverage']:.3f}, accepted_precision={test['accepted_precision']:.3f}, "
        f"rejected_aware_accuracy={test['rejected_aware_accuracy']:.3f}, raw_accuracy={test['raw_accuracy']:.3f}"
    )
    print(f"Report: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
