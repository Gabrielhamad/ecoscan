from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.classification.baseline import KNearestNeighborsClassifier, NearestCentroidClassifier
from ecoscan.classification.features import FeatureConfig, extract_features
from ecoscan.config import load_config
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.metrics.classification_metrics import classification_report


def _iter_split_images(split_dir: Path, classes: list[str], extensions: frozenset[str]) -> list[tuple[Path, str]]:
    items: list[tuple[Path, str]] = []
    for class_id in classes:
        class_dir = split_dir / class_id
        if not class_dir.exists():
            continue
        for path in sorted(class_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in extensions:
                items.append((path, class_id))
    return items


def _load_features(items: list[tuple[Path, str]], feature_config: FeatureConfig, min_size: tuple[int, int], extensions: frozenset[str]) -> tuple[np.ndarray, list[str], list[str]]:
    features = []
    labels = []
    paths = []
    for path, label in items:
        loaded = load_rgb_image(path, allowed_extensions=extensions, min_size=min_size)
        features.append(extract_features(loaded.array, feature_config))
        labels.append(label)
        paths.append(path.as_posix())
    if not features:
        return np.empty((0, 0), dtype=np.float32), labels, paths
    return np.vstack(features), labels, paths


def _write_report_csv(
    path: Path,
    labels: list[str],
    raw_predictions: list[str],
    accepted_predictions: list[str | None],
    probabilities: list[float],
    source_paths: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "path",
                "true_label",
                "raw_predicted_label",
                "accepted_predicted_label",
                "probability",
            ],
        )
        writer.writeheader()
        for source_path, label, raw_prediction, accepted_prediction, probability in zip(
            source_paths,
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


def _evaluate(
    classifier: NearestCentroidClassifier,
    features: np.ndarray,
    labels: list[str],
    paths: list[str],
    classes: list[str],
    output_dir: Path,
    split_name: str,
) -> dict:
    raw_predictions = []
    accepted_predictions = []
    probabilities = []
    for feature in features:
        prediction = classifier.predict(feature)
        raw_predictions.append(prediction.top_class_id)
        accepted_predictions.append(prediction.class_id)
        probabilities.append(prediction.probability)

    report = {
        "raw_top1": classification_report(labels, raw_predictions, classes),
        "with_rejection": classification_report(labels, accepted_predictions, classes),
    }
    _write_report_csv(
        output_dir / f"{split_name}_predictions.csv",
        labels,
        raw_predictions,
        accepted_predictions,
        probabilities,
        paths,
    )
    (output_dir / f"{split_name}_metrics.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a simple EcoScan baseline classifier.")
    parser.add_argument("--output-model", type=Path, default=PROJECT_ROOT / "models" / "baseline_classifier.json")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "baseline")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    baseline_config = config.baseline
    feature_config = FeatureConfig(
        image_size=tuple(baseline_config.get("image_size", [96, 96])),
        histogram_bins=int(baseline_config.get("histogram_bins", 8)),
    )
    algorithm = str(baseline_config.get("algorithm", "knn"))
    threshold = float(baseline_config.get("confidence_threshold", config.confidence_threshold))
    softmax_temperature = float(baseline_config.get("softmax_temperature", 1.0))
    k_neighbors = int(baseline_config.get("k_neighbors", 5))
    classes = list(config.classes)

    train_items = _iter_split_images(config.directories["train_data"], classes, config.allowed_extensions)
    validation_items = _iter_split_images(config.directories["validation_data"], classes, config.allowed_extensions)
    test_items = _iter_split_images(config.directories["test_data"], classes, config.allowed_extensions)
    if not train_items:
        print("No training images found. Run scripts\\split_dataset.py --overwrite first.")
        return 1

    train_features, train_labels, _ = _load_features(train_items, feature_config, config.min_image_size, config.allowed_extensions)
    if algorithm == "nearest_centroid":
        classifier = NearestCentroidClassifier.fit(
            train_features,
            train_labels,
            threshold=threshold,
            softmax_temperature=softmax_temperature,
        )
    elif algorithm == "knn":
        classifier = KNearestNeighborsClassifier.fit(
            train_features,
            train_labels,
            threshold=threshold,
            k_neighbors=k_neighbors,
        )
    else:
        print(f"Unsupported baseline algorithm: {algorithm}")
        return 1
    model_path = classifier.save(
        args.output_model,
        metadata={
            "algorithm": algorithm,
            "feature_config": {
                "image_size": list(feature_config.image_size),
                "histogram_bins": feature_config.histogram_bins,
                "softmax_temperature": softmax_temperature,
                "k_neighbors": k_neighbors,
            },
            "note": "Baseline academica simples; scores nao sao calibrados como uma rede neural.",
        },
    )

    args.report_dir.mkdir(parents=True, exist_ok=True)
    reports = {}
    for split_name, items in [("validation", validation_items), ("test", test_items)]:
        features, labels, paths = _load_features(items, feature_config, config.min_image_size, config.allowed_extensions)
        reports[split_name] = _evaluate(classifier, features, labels, paths, classes, args.report_dir, split_name)

    summary_path = args.report_dir / "baseline_summary.json"
    summary_path.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")

    print("EcoScan baseline trained.")
    print(f"Model: {model_path}")
    for split_name, report in reports.items():
        raw_report = report["raw_top1"]
        rejected_report = report["with_rejection"]
        print(
            f"{split_name}: raw_accuracy={raw_report['accuracy']:.3f}, "
            f"raw_macro_f1={raw_report['macro_f1']:.3f}, "
            f"accepted_accuracy={rejected_report['accuracy']:.3f}, "
            f"uncertain={rejected_report['uncertain_count']}/{rejected_report['total']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
