from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from ecoscan.app.pipeline import ProcessingPipelineOptions
from ecoscan.config import load_config
from ecoscan.metrics.classification_metrics import (
    classification_report,
    write_confusion_matrix_csv,
    write_confusion_matrix_image,
)
from ecoscan.services.analysis_service import analyze_waste_image, load_model_bundle_for_analysis
from train_baseline import _iter_split_images


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate the full EcoScan app analysis pipeline on a split.")
    parser.add_argument("--split", choices=["train", "validation", "test"], default="test")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "evaluation" / "app_analysis_test")
    return parser


def _write_predictions(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "path",
        "true_label",
        "predicted_label",
        "top_label",
        "probability",
        "accepted",
        "model_type",
        "filter",
        "segmentation",
        "elements",
        "material_rule",
        "message",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    classes = list(config.classes)
    split_dir = config.directories[f"{args.split}_data"]
    items = _iter_split_images(split_dir, classes, config.allowed_extensions)
    if not items:
        print(f"No images found in split: {split_dir}")
        return 1

    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = load_model_bundle_for_analysis(config)
    options = ProcessingPipelineOptions(filter_name="auto", segmentation_name="auto")

    labels: list[str] = []
    predictions: list[str | None] = []
    rows: list[dict[str, str]] = []
    material_rule_counts: dict[str, int] = {}

    for path, label in items:
        result = analyze_waste_image(path, config, options=options, model_bundle=bundle)
        labels.append(label)
        predictions.append(result.predicted_class)
        rule_id = result.material_rule.rule_id if result.material_rule else ""
        if rule_id:
            material_rule_counts[rule_id] = material_rule_counts.get(rule_id, 0) + 1
        rows.append(
            {
                "path": path.as_posix(),
                "true_label": label,
                "predicted_label": result.predicted_class or "__uncertain__",
                "top_label": result.top_class or "__none__",
                "probability": f"{(result.probability or 0.0):.6f}",
                "accepted": str(result.accepted).lower(),
                "model_type": result.model_type,
                "filter": result.pipeline.filter_result.name,
                "segmentation": result.pipeline.segmentation_result.name,
                "elements": str(result.pipeline.element_analysis.significant_count),
                "material_rule": rule_id,
                "message": result.message,
            }
        )

    report = classification_report(labels, predictions, classes)
    report["split"] = args.split
    report["model_kind"] = "full_app_analysis"
    report["material_rule_counts"] = material_rule_counts
    (output_dir / "metrics.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_predictions(output_dir / "predictions.csv", rows)
    write_confusion_matrix_csv(report["confusion_matrix"], classes, output_dir / "confusion_matrix.csv")
    write_confusion_matrix_image(report["confusion_matrix"], classes, output_dir / "confusion_matrix.png")

    print("EcoScan app analysis evaluation complete.")
    print(f"Split: {args.split}")
    print(f"Accuracy: {report['accuracy']:.3f}")
    print(f"Macro F1: {report['macro_f1']:.3f}")
    print(f"Uncertain: {report['uncertain_count']}/{report['total']}")
    print(f"Material rules: {material_rule_counts}")
    print(f"Output: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
