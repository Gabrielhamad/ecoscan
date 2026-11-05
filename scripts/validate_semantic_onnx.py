"""Evaluate the compact model on fixed test images and known regressions."""
import argparse
import csv
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ecoscan.app.pipeline import default_processing_options, run_processing_pipeline
from ecoscan.classification.semantic_onnx import SemanticOnnxClassifier
from ecoscan.config import load_config
from ecoscan.metrics.classification_metrics import classification_report
from ecoscan.services.evaluation_manifest import audit_evaluation_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("model", "manifest", "source", "cases", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--require-groups", action="store_true",
                        help="Reject object or capture session overlap across supplied splits")
    parser.add_argument("--development-hashes", type=Path,
                        help="Optional JSON array of SHA-256 hashes from known development data")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a new report path")
    config = load_config()
    records = json.loads(args.manifest.read_text(encoding="utf-8"))
    development_hashes = ()
    if args.development_hashes:
        development_hashes = json.loads(args.development_hashes.read_text(encoding="utf-8"))
        if not isinstance(development_hashes, list):
            raise ValueError("Development hashes must be a JSON array")
    audit = audit_evaluation_manifest(
        records,
        allowed_classes=config.classes,
        require_groups=args.require_groups,
        development_hashes=development_hashes,
    )
    model = SemanticOnnxClassifier(args.model)
    options = replace(default_processing_options(config), segmentation_name="none", morphology_name="none")
    source = args.source.resolve()
    labels, accepted, top = [], [], []
    for row in records:
        if row["split"] != "test":
            continue
        path = (source / row["path"]).resolve()
        if not path.is_relative_to(source) or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Source changed")
        prediction = model.predict_image(run_processing_pipeline(path, config, options).recognition_image)
        labels.append(row["class_id"])
        top.append(prediction.top_class_id)
        accepted.append(prediction.class_id)
    evaluation_classes = [class_id for class_id in config.classes if class_id in set(labels)]
    if not evaluation_classes:
        raise ValueError("The test manifest has no supported class labels")
    accepted_total = sum(value is not None for value in accepted)
    accepted_correct = sum(expected == prediction for expected, prediction in zip(labels, accepted, strict=True))
    result = {
        "schema_version": 2,
        "manifest_audit": audit,
        "independent_test": False,
        "evaluation_classes": evaluation_classes,
        "integrity": {
            "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
            "model_metadata_sha256": hashlib.sha256(args.model.read_bytes()).hexdigest(),
            "head_sha256": model.metadata["head_sha256"],
            "encoder_sha256": model.metadata["encoder_sha256"],
            "processing_sha256": model.metadata["processing"]["sha256"],
        },
        "top1": classification_report(labels, top, evaluation_classes),
        "accepted": classification_report(labels, accepted, evaluation_classes),
        "acceptance": {
            "threshold": model.metadata["threshold"],
            "accepted": accepted_total,
            "correct": accepted_correct,
            "wrong": accepted_total - accepted_correct,
            "rejected": len(labels) - accepted_total,
        },
        "cases": [],
    }
    with args.cases.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            prediction = model.predict_image(run_processing_pipeline(Path(row["path"]), config, options).recognition_image)
            result["cases"].append({"expected": row["expected_class"], "top": prediction.top_class_id,
                                    "accepted": prediction.accepted, "score": prediction.probability})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"top1_accuracy": result["top1"]["accuracy"],
                      "accepted_accuracy_over_all": result["accepted"]["accuracy"],
                      **result["acceptance"], "cases": result["cases"]}))


if __name__ == "__main__":
    main()
