"""Compare a trained candidate with the bundled SVM without changing production."""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ecoscan.app.pipeline import default_processing_options, run_processing_pipeline
from ecoscan.classification.deep_features import DeepFeatureClassifier
from ecoscan.classification.visual_svm import VisualSvmClassifier
from ecoscan.config import load_config
from ecoscan.metrics.classification_metrics import classification_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--cases", type=Path, help="Optional JSON with path and expected_class")
    args = parser.parse_args()
    config = load_config()
    candidate = DeepFeatureClassifier.load(args.candidate, config)
    baseline = VisualSvmClassifier.load(config.directories["models"] / "vision_svm_classifier.joblib")
    records = json.loads((args.candidate / "dataset_manifest.json").read_text(encoding="utf-8"))
    source = args.source.resolve()
    models = {"bundled_svm": baseline, "candidate": candidate}
    labels, predicted, top = [], {name: [] for name in models}, {name: [] for name in models}
    options = replace(default_processing_options(config), segmentation_name="none", morphology_name="none")
    for row in records:
        if row["split"] != "test":
            continue
        path = (source / row["path"]).resolve()
        if not path.is_relative_to(source) or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Test image changed")
        prepared = run_processing_pipeline(path, config, options).recognition_image
        labels.append(row["class_id"])
        for name, model in models.items():
            prediction = model.predict_image(prepared)
            predicted[name].append(prediction.class_id)
            top[name].append(prediction.top_class_id)
    result = {"test_count": len(labels), "production_changed": False,
              "warning": "Historical test reused in experiments; not blind acceptance. Bundled SVM training overlap is unknown.",
              "models": {name: {"accepted": classification_report(labels, predicted[name], config.classes),
                                "top1": classification_report(labels, top[name], config.classes)} for name in models}}
    result["regression_cases"] = []
    if args.cases:
        known_hashes = {row["sha256"] for row in records}
        for index, row in enumerate(json.loads(args.cases.read_text(encoding="utf-8"))):
            path = Path(row["path"])
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest in known_hashes:
                raise ValueError("Regression case already in training reference")
            prepared = run_processing_pipeline(path, config, options).recognition_image
            result["regression_cases"].append({"case": index + 1, "sha256": digest,
                "expected": row["expected_class"],
                "predictions": {name: asdict(model.predict_image(prepared)) for name, model in models.items()}})
    (args.candidate / "comparison.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"test_count": result["test_count"], "models": {
        name: {"top1_accuracy": scores["top1"]["accuracy"], "accepted_recall": scores["accepted"]["accuracy"],
               "uncertain_count": scores["accepted"]["uncertain_count"]} for name, scores in result["models"].items()},
        "regression_cases": result["regression_cases"]}, indent=2))


if __name__ == "__main__":
    main()
