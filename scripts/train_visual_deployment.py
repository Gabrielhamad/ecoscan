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
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from ecoscan.classification.visual_features import VisualFeatureConfig, extract_visual_features
from ecoscan.classification.visual_knn import VisualKnnClassifier
from ecoscan.config import load_config
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.metrics.classification_metrics import classification_report
from train_baseline import _iter_split_images


def _load_features(
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


def _write_predictions(
    path: Path,
    labels: list[str],
    predictions: list[str | None],
    probabilities: list[float],
    paths: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["path", "true_label", "predicted_label", "probability"])
        writer.writeheader()
        for source_path, label, prediction, probability in zip(paths, labels, predictions, probabilities, strict=True):
            writer.writerow(
                {
                    "path": source_path,
                    "true_label": label,
                    "predicted_label": prediction or "__uncertain__",
                    "probability": f"{probability:.6f}",
                }
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the deployment EcoScan visual model with all approved processed images.")
    parser.add_argument("--source", type=Path, default=PROJECT_ROOT / "data" / "processed")
    parser.add_argument("--output-model", type=Path, default=PROJECT_ROOT / "models" / "vision_classifier.npz")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "visual_deployment_training")
    parser.add_argument("--threshold", type=float, default=0.10)
    parser.add_argument("--k-neighbors", type=int, default=11)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    classes = list(config.classes)
    feature_config = VisualFeatureConfig(image_size=(96, 96), rgb_histogram_bins=12, hsv_histogram_bins=10)
    items = _iter_split_images(args.source, classes, config.allowed_extensions)
    if not items:
        print(f"No processed images found in {args.source}.")
        return 1

    features, labels, paths = _load_features(
        items,
        feature_config,
        min_size=config.min_image_size,
        extensions=config.allowed_extensions,
    )
    classifier = VisualKnnClassifier.fit(
        features,
        labels,
        classes=classes,
        feature_config=feature_config,
        threshold=args.threshold,
        k_neighbors=args.k_neighbors,
        distance_metric="cosine",
        score_mode="neighbor_vote",
        notes=[
            "Modelo de operação treinado com todas as imagens processadas e aprovadas.",
            "Os relatórios de validação/teste continuam separados; este arquivo prioriza repertório para uso no app.",
            "Usa descritores RGB/HSV, HOG e LBP após filtragem e segmentação do pipeline EcoScan.",
        ],
    )
    model_path = classifier.save(args.output_model)

    predictions: list[str | None] = []
    probabilities: list[float] = []
    for feature in classifier.features:
        prediction = classifier.predict_feature(feature)
        predictions.append(prediction.class_id)
        probabilities.append(prediction.probability)

    report = classification_report(labels, predictions, classes)
    report["model_path"] = str(model_path)
    report["source"] = str(args.source)
    report["training_mode"] = "deployment_all_processed"
    report["note"] = "Métrica aparente sobre o próprio conjunto de operação; não substitui validação holdout."

    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "deployment_metrics.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_predictions(args.report_dir / "deployment_predictions.csv", labels, predictions, probabilities, paths)

    print("EcoScan deployment visual model trained.")
    print(f"Model: {model_path}")
    print(f"Images: {len(labels)}")
    print(f"Self-check accuracy: {report['accuracy']:.3f}")
    print(f"Self-check macro F1: {report['macro_f1']:.3f}")
    print(f"Report: {args.report_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
