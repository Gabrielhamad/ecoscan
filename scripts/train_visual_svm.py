from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from typing import Callable
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from ecoscan.classification.visual_features import VisualFeatureConfig, extract_visual_features
from ecoscan.classification.visual_svm import VisualSvmClassifier, VisualSvmMetadata
from ecoscan.config import load_config
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.metrics.classification_metrics import classification_report
from train_baseline import _iter_split_images


@dataclass(frozen=True)
class ModelCandidate:
    name: str
    build: Callable[[], object]
    metadata: dict[str, object]


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


def _predict_many(classifier: VisualSvmClassifier, features: np.ndarray) -> tuple[list[str], list[str | None], list[float]]:
    raw_predictions: list[str] = []
    accepted_predictions: list[str | None] = []
    probabilities: list[float] = []
    for feature in features:
        prediction = classifier.predict_feature(feature[None, :])
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


def _evaluate(
    classifier: VisualSvmClassifier,
    features: np.ndarray,
    labels: list[str],
    paths: list[str],
    classes: list[str],
    output_dir: Path,
    split_name: str,
) -> dict:
    raw_predictions, accepted_predictions, probabilities = _predict_many(classifier, features)
    report = {
        "raw_top1": classification_report(labels, raw_predictions, classes),
        "with_rejection": classification_report(labels, accepted_predictions, classes),
    }
    _write_predictions(
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


def _build_candidates(random_seed: int) -> list[ModelCandidate]:
    from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC

    return [
        ModelCandidate(
            name="visual_svc_rbf_c3",
            build=lambda: make_pipeline(
                StandardScaler(),
                SVC(
                    C=3.0,
                    gamma="scale",
                    kernel="rbf",
                    class_weight="balanced",
                    decision_function_shape="ovr",
                    random_state=random_seed,
                ),
            ),
            metadata={"kernel": "rbf", "c_value": 3.0, "gamma": "scale", "class_weight": "balanced"},
        ),
        ModelCandidate(
            name="visual_svc_rbf_c10",
            build=lambda: make_pipeline(
                StandardScaler(),
                SVC(
                    C=10.0,
                    gamma="scale",
                    kernel="rbf",
                    class_weight="balanced",
                    decision_function_shape="ovr",
                    random_state=random_seed,
                ),
            ),
            metadata={"kernel": "rbf", "c_value": 10.0, "gamma": "scale", "class_weight": "balanced"},
        ),
        ModelCandidate(
            name="visual_logistic_regression",
            build=lambda: make_pipeline(
                StandardScaler(),
                LogisticRegression(
                    C=2.0,
                    class_weight="balanced",
                    max_iter=2500,
                    random_state=random_seed,
                ),
            ),
            metadata={"kernel": "linear", "c_value": 2.0, "gamma": "n/a", "class_weight": "balanced"},
        ),
        ModelCandidate(
            name="visual_extra_trees",
            build=lambda: ExtraTreesClassifier(
                n_estimators=450,
                class_weight="balanced",
                max_features="sqrt",
                min_samples_leaf=1,
                random_state=random_seed,
                n_jobs=-1,
            ),
            metadata={"kernel": "ensemble", "c_value": 0.0, "gamma": "n/a", "class_weight": "balanced"},
        ),
        ModelCandidate(
            name="visual_random_forest",
            build=lambda: RandomForestClassifier(
                n_estimators=350,
                class_weight="balanced",
                max_features="sqrt",
                min_samples_leaf=1,
                random_state=random_seed,
                n_jobs=-1,
            ),
            metadata={"kernel": "ensemble", "c_value": 0.0, "gamma": "n/a", "class_weight": "balanced"},
        ),
    ]


def _wrap_model(
    *,
    model: object,
    labels: list[str],
    feature_config: VisualFeatureConfig,
    threshold: float,
    candidate: ModelCandidate,
    notes: list[str],
) -> VisualSvmClassifier:
    classes = [str(class_id) for class_id in getattr(model, "classes_", sorted(set(labels)))]
    metadata = VisualSvmMetadata(
        algorithm=candidate.name,
        feature_config=feature_config,
        threshold=threshold,
        kernel=str(candidate.metadata.get("kernel", candidate.name)),
        c_value=float(candidate.metadata.get("c_value", 0.0)),
        gamma=candidate.metadata.get("gamma", "n/a"),
        class_weight=(
            str(candidate.metadata["class_weight"])
            if candidate.metadata.get("class_weight") is not None
            else None
        ),
        train_count=len(labels),
        notes=notes,
    )
    return VisualSvmClassifier(model=model, classes=classes, metadata=metadata)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the EcoScan visual SVM classifier.")
    parser.add_argument("--output-model", type=Path, default=PROJECT_ROOT / "models" / "vision_svm_classifier.joblib")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "visual_svm_training")
    parser.add_argument("--threshold", type=float, default=0.10)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    classes = list(config.classes)
    feature_config = VisualFeatureConfig(image_size=(96, 96), rgb_histogram_bins=12, hsv_histogram_bins=10)

    train_items = _iter_split_images(config.directories["train_data"], classes, config.allowed_extensions)
    validation_items = _iter_split_images(config.directories["validation_data"], classes, config.allowed_extensions)
    test_items = _iter_split_images(config.directories["test_data"], classes, config.allowed_extensions)
    if not train_items:
        print("No training images found. Run scripts\\split_dataset.py --source data\\processed --overwrite first.")
        return 1

    args.report_dir.mkdir(parents=True, exist_ok=True)
    train_features, train_labels, _ = _load_visual_features(
        train_items,
        feature_config,
        min_size=config.min_image_size,
        extensions=config.allowed_extensions,
    )
    validation_features, validation_labels, validation_paths = _load_visual_features(
        validation_items,
        feature_config,
        min_size=config.min_image_size,
        extensions=config.allowed_extensions,
    )

    notes = [
        "Modelo visual supervisionado treinado sobre imagens preparadas pelo pipeline de processamento.",
        "Usa descritores RGB/HSV, HOG e LBP para equilibrar cor, forma e textura.",
        "Criado como modelo de operação inicial até o transfer learning final com dataset curado.",
    ]
    candidate_rows: list[dict[str, object]] = []
    ranked_classifiers: list[tuple[dict, VisualSvmClassifier, ModelCandidate]] = []
    for candidate in _build_candidates(config.random_seed):
        model = candidate.build()
        model.fit(train_features, train_labels)  # type: ignore[attr-defined]
        classifier = _wrap_model(
            model=model,
            labels=train_labels,
            feature_config=feature_config,
            threshold=args.threshold,
            candidate=candidate,
            notes=notes,
        )
        validation_report = _evaluate(
            classifier,
            validation_features,
            validation_labels,
            validation_paths,
            classes,
            args.report_dir / "candidates" / candidate.name,
            "validation",
        )
        raw_report = validation_report["raw_top1"]
        candidate_rows.append(
            {
                "candidate": candidate.name,
                "validation_accuracy": raw_report["accuracy"],
                "validation_macro_f1": raw_report["macro_f1"],
                "validation_uncertain": validation_report["with_rejection"]["uncertain_count"],
            }
        )
        ranked_classifiers.append((raw_report, classifier, candidate))

    ranked_classifiers.sort(
        key=lambda item: (item[0]["macro_f1"], item[0]["accuracy"]),
        reverse=True,
    )
    _, classifier, selected_candidate = ranked_classifiers[0]
    model_path = classifier.save(args.output_model)

    with (args.report_dir / "model_selection.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["candidate", "validation_accuracy", "validation_macro_f1", "validation_uncertain"])
        writer.writeheader()
        writer.writerows(candidate_rows)

    reports = {}
    for split_name, items in [("validation", validation_items), ("test", test_items)]:
        features, labels, paths = _load_visual_features(
            items,
            feature_config,
            min_size=config.min_image_size,
            extensions=config.allowed_extensions,
        )
        reports[split_name] = _evaluate(classifier, features, labels, paths, classes, args.report_dir, split_name)

    summary = {
        "model_path": str(model_path),
        "feature_config": feature_config.to_dict(),
        "algorithm": classifier.metadata.algorithm,
        "selected_candidate": selected_candidate.name,
        "candidate_ranking": candidate_rows,
        "threshold": args.threshold,
        "reports": reports,
    }
    (args.report_dir / "visual_svm_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("EcoScan visual SVM trained.")
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
    print(f"Report: {args.report_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
