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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("model", "manifest", "source", "cases", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a new report path")
    config = load_config()
    model = SemanticOnnxClassifier(args.model)
    options = replace(default_processing_options(config), segmentation_name="none", morphology_name="none")
    source = args.source.resolve()
    labels, accepted, top = [], [], []
    for row in json.loads(args.manifest.read_text(encoding="utf-8")):
        if row["split"] != "test":
            continue
        path = (source / row["path"]).resolve()
        if not path.is_relative_to(source) or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Source changed")
        prediction = model.predict_image(run_processing_pipeline(path, config, options).recognition_image)
        labels.append(row["class_id"])
        top.append(prediction.top_class_id)
        accepted.append(prediction.class_id)
    result = {"top1": classification_report(labels, top, config.classes),
              "accepted": classification_report(labels, accepted, config.classes), "cases": []}
    with args.cases.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            prediction = model.predict_image(run_processing_pipeline(Path(row["path"]), config, options).recognition_image)
            result["cases"].append({"expected": row["expected_class"], "top": prediction.top_class_id,
                                    "accepted": prediction.accepted, "score": prediction.probability})
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"top1_accuracy": result["top1"]["accuracy"],
                      "accepted_accuracy_over_all": result["accepted"]["accuracy"],
                      "uncertain": result["accepted"]["uncertain_count"], "cases": result["cases"]}))


if __name__ == "__main__":
    main()
