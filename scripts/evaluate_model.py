from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.classification.inference import (
    load_baseline_model,
    load_visual_knn_model,
    load_visual_svm_model,
    predict_with_baseline,
    predict_with_visual_knn,
    predict_with_visual_svm,
)
from ecoscan.app.pipeline import run_processing_pipeline
from ecoscan.config import load_config
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.image_processing.preprocessing import prepare_model_input
from ecoscan.metrics.classification_metrics import (
    classification_report,
    write_confusion_matrix_csv,
    write_confusion_matrix_image,
)


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


def _prediction_image(path: Path, config: Any, *, use_pipeline: bool) -> np.ndarray:
    if use_pipeline:
        return run_processing_pipeline(path, config).segmentation_result.image
    return load_rgb_image(path, allowed_extensions=config.allowed_extensions, min_size=config.min_image_size).array


def _baseline_predictions(
    model_path: Path,
    items: list[tuple[Path, str]],
    config: Any,
    *,
    use_pipeline: bool,
) -> tuple[list[str], list[str | None], list[float], list[str]]:
    bundle = load_baseline_model(model_path)
    labels: list[str] = []
    predictions: list[str | None] = []
    probabilities: list[float] = []
    paths: list[str] = []

    for path, label in items:
        image = _prediction_image(path, config, use_pipeline=use_pipeline)
        prediction = predict_with_baseline(image, bundle)
        labels.append(label)
        predictions.append(prediction.class_id)
        probabilities.append(prediction.probability)
        paths.append(path.as_posix())
    return labels, predictions, probabilities, paths


def _visual_knn_predictions(
    model_path: Path,
    items: list[tuple[Path, str]],
    config: Any,
    *,
    use_pipeline: bool,
) -> tuple[list[str], list[str | None], list[float], list[str]]:
    bundle = load_visual_knn_model(model_path)
    labels: list[str] = []
    predictions: list[str | None] = []
    probabilities: list[float] = []
    paths: list[str] = []

    for path, label in items:
        image = _prediction_image(path, config, use_pipeline=use_pipeline)
        prediction = predict_with_visual_knn(image, bundle)
        labels.append(label)
        predictions.append(prediction.class_id)
        probabilities.append(prediction.probability)
        paths.append(path.as_posix())
    return labels, predictions, probabilities, paths


def _visual_svm_predictions(
    model_path: Path,
    items: list[tuple[Path, str]],
    config: Any,
    *,
    use_pipeline: bool,
) -> tuple[list[str], list[str | None], list[float], list[str]]:
    bundle = load_visual_svm_model(model_path)
    labels: list[str] = []
    predictions: list[str | None] = []
    probabilities: list[float] = []
    paths: list[str] = []

    for path, label in items:
        image = _prediction_image(path, config, use_pipeline=use_pipeline)
        prediction = predict_with_visual_svm(image, bundle)
        labels.append(label)
        predictions.append(prediction.class_id)
        probabilities.append(prediction.probability)
        paths.append(path.as_posix())
    return labels, predictions, probabilities, paths


def _tensorflow_predictions(
    model_path: Path,
    items: list[tuple[Path, str]],
    config: Any,
    *,
    use_pipeline: bool,
) -> tuple[list[str], list[str | None], list[float], list[str]]:
    try:
        import tensorflow as tf  # type: ignore
    except ImportError as exc:
        raise RuntimeError("TensorFlow is required to evaluate .keras models.") from exc

    class_names_path = config.project_root / str(config.model.get("class_names_path", "models/class_names.json"))
    if not class_names_path.exists():
        raise FileNotFoundError(f"Class names file not found: {class_names_path}")
    class_names = json.loads(class_names_path.read_text(encoding="utf-8"))
    model = tf.keras.models.load_model(model_path)

    labels: list[str] = []
    predictions: list[str | None] = []
    probabilities: list[float] = []
    paths: list[str] = []
    for path, label in items:
        image = _prediction_image(path, config, use_pipeline=use_pipeline)
        prepared = prepare_model_input(image, config.image_size)
        probs = np.asarray(model.predict(prepared.model_input, verbose=0)[0], dtype=np.float32)
        best_index = int(np.argmax(probs))
        probability = float(probs[best_index])
        predicted_class = class_names[best_index] if probability >= config.confidence_threshold else None
        labels.append(label)
        predictions.append(predicted_class)
        probabilities.append(probability)
        paths.append(path.as_posix())
    return labels, predictions, probabilities, paths


def _write_predictions(path: Path, labels: list[str], predictions: list[str | None], probabilities: list[float], paths: list[str]) -> None:
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
    parser = argparse.ArgumentParser(description="Evaluate EcoScan baseline or final model on a split.")
    parser.add_argument("--model", type=Path, default=PROJECT_ROOT / "models" / "baseline_classifier.json")
    parser.add_argument("--split", choices=["train", "validation", "test"], default="test")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--use-pipeline", action="store_true", help="Run the same filtering and segmentation path used by the app before prediction.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    classes = list(config.classes)
    split_dir = config.directories[f"{args.split}_data"]
    items = _iter_split_images(split_dir, classes, config.allowed_extensions)
    if not items:
        print(f"No images found in split: {split_dir}")
        return 1

    output_dir = args.output or config.directories["reports"] / "evaluation" / args.split
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.model.suffix.lower() == ".json":
        labels, predictions, probabilities, paths = _baseline_predictions(args.model, items, config, use_pipeline=args.use_pipeline)
        model_kind = "baseline_json"
    elif args.model.suffix.lower() == ".npz":
        labels, predictions, probabilities, paths = _visual_knn_predictions(args.model, items, config, use_pipeline=args.use_pipeline)
        model_kind = "visual_knn_npz"
    elif args.model.suffix.lower() in {".joblib", ".pkl"}:
        labels, predictions, probabilities, paths = _visual_svm_predictions(args.model, items, config, use_pipeline=args.use_pipeline)
        model_kind = "visual_svm_joblib"
    elif args.model.suffix.lower() == ".keras":
        labels, predictions, probabilities, paths = _tensorflow_predictions(args.model, items, config, use_pipeline=args.use_pipeline)
        model_kind = "tensorflow_keras"
    else:
        print(f"Unsupported model file: {args.model}")
        return 1

    report = classification_report(labels, predictions, classes)
    report["model_kind"] = model_kind
    report["model_path"] = str(args.model)
    report["split"] = args.split
    report["use_pipeline"] = args.use_pipeline

    (output_dir / "metrics.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_predictions(output_dir / "predictions.csv", labels, predictions, probabilities, paths)
    write_confusion_matrix_csv(report["confusion_matrix"], classes, output_dir / "confusion_matrix.csv")
    write_confusion_matrix_image(report["confusion_matrix"], classes, output_dir / "confusion_matrix.png")

    print("EcoScan evaluation complete.")
    print(f"Model kind: {model_kind}")
    print(f"Split: {args.split}")
    print(f"Accuracy: {report['accuracy']:.3f}")
    print(f"Macro F1: {report['macro_f1']:.3f}")
    print(f"Uncertain: {report['uncertain_count']}/{report['total']}")
    print(f"Output: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
