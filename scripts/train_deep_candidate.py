"""Train an isolated, reproducible CPU candidate without changing the public model."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import shutil
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import cv2
import joblib
import numpy as np
import sklearn
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from PIL import Image

from ecoscan.app.pipeline import default_processing_options, run_processing_pipeline
from ecoscan.classification.deep_features import BACKBONE_SHA256, BACKBONE_URL, MobileNetFeatures
from ecoscan.classification.visual_svm import VisualSvmClassifier
from ecoscan.config import load_config
from ecoscan.image_processing.contracts import processing_contract, write_model_contract
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.image_processing.preprocessing import prepare_working_image
from ecoscan.training.grouped_split import grouped_split, image_groups
from ecoscan.training.augmentation import AUGMENTATION_VERSION, capture_variants, training_indices
from ecoscan.training.heads import build_head


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _capture_groups(path, source):
    if path is None:
        return {}
    groups = {}
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            image = (source / row["path"]).resolve()
            if not image.is_relative_to(source) or not row["group_id"].strip() or image in groups:
                raise ValueError("Invalid or duplicate capture group manifest entry.")
            groups[image] = row["group_id"].strip()
    return groups


def _report(labels, probabilities, classes, threshold):
    indices = probabilities.argmax(axis=1)
    predictions = np.asarray(classes)[indices]
    accepted = probabilities.max(axis=1) >= threshold
    return {
        "top1": classification_report(labels, predictions, labels=classes, output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(labels, predictions, labels=classes).tolist(),
        "classes": classes,
        "threshold": threshold,
        "coverage": float(accepted.mean()),
        "accepted_count": int(accepted.sum()),
        "accepted_accuracy": float((predictions[accepted] == np.asarray(labels)[accepted]).mean()) if accepted.any() else None,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Analyst-curated class folders")
    parser.add_argument("--backbone", type=Path, required=True, help="Official mobilenetv2-12.onnx")
    parser.add_argument("--output", type=Path, required=True, help="NEW isolated run directory")
    parser.add_argument("--groups", type=Path, help="CSV path,group_id: same object/capture session together")
    parser.add_argument("--resume", action="store_true", help="Reuse verified per-image checkpoints")
    parser.add_argument("--representation", choices=("embedding", "logits"), default="embedding")
    parser.add_argument("--augment", action="store_true", help="Compare train-only capture variations with originals")
    parser.add_argument("--feature-cache", type=Path, help="Read verified original features from a previous run")
    parser.add_argument("--heads", choices=("logistic", "compare"), default="logistic",
                        help="Compare logistic regression and group-calibrated nonlinear SVM")
    args = parser.parse_args(argv)
    config = load_config()
    if config.image_size != (224, 224):
        raise ValueError("This backbone requires the 224x224 preparation contract.")
    source, output = args.source.resolve(), args.output.resolve()
    if not source.is_dir() or (output.exists() and not args.resume):
        raise ValueError("Source must exist and output must be a NEW directory.")
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Source and output must be isolated.")
    if output.is_relative_to(config.directories["models"]):
        raise ValueError("Save training runs outside the active models directory.")
    backbone = MobileNetFeatures(args.backbone, args.representation)
    captures = _capture_groups(args.groups, source)
    paths = [(label, path) for label in config.classes for path in sorted((source / label).glob("*"))
             if path.is_file() and path.suffix.lower() in config.allowed_extensions]
    if any(sum(y == label for y, _ in paths) < 20 for label in config.classes):
        raise ValueError("At least 20 curated images per configured class are required.")
    if args.groups and set(captures) != {path.resolve() for _, path in paths}:
        raise ValueError("Capture group CSV must cover every selected image exactly once.")
    output.mkdir(parents=True, exist_ok=True)
    (output / "features").mkdir(exist_ok=True)
    cv2.setNumThreads(2)
    baseline_path = config.directories["models"] / "vision_svm_classifier.joblib"
    baseline = VisualSvmClassifier.load(baseline_path) if baseline_path.exists() else None
    if baseline and "n_jobs" in baseline.model.get_params():
        baseline.model.set_params(n_jobs=1)
    records, features, baseline_predictions = [], [], []
    # Diagnostic masks do not feed recognition; skip their costly rendering in batch training.
    options = replace(default_processing_options(config), segmentation_name="none", morphology_name="none")
    contract = processing_contract(config)
    cache_profile = {"source": str(source), "processing": contract["sha256"],
                     "representation": args.representation,
                     "backbone": BACKBONE_SHA256,
                     "baseline": _digest(baseline_path.read_bytes()) if baseline else None}
    profile_path = output / "cache_profile.json"
    if profile_path.exists() and json.loads(profile_path.read_text(encoding="utf-8")) != cache_profile:
        raise ValueError("Checkpoint does not match this source, processing or baseline.")
    profile_path.write_text(json.dumps(cache_profile, indent=2), encoding="utf-8")
    if args.feature_cache:
        previous = args.feature_cache.resolve()
        if json.loads((previous / "cache_profile.json").read_text(encoding="utf-8")) != cache_profile:
            raise ValueError("Feature cache has a different preparation, backbone or source.")

    def extract(item):
        label, path = item
        original_hash = _digest(path.read_bytes())
        cache_key = _digest((label + path.relative_to(source).as_posix() + original_hash).encode())
        feature_path = output / "features" / f"{cache_key}.npy"
        record_path = output / "features" / f"{cache_key}.json"
        if args.feature_cache and not feature_path.exists() and not record_path.exists():
            old_feature = previous / "features" / feature_path.name
            old_record = previous / "features" / record_path.name
            if old_feature.exists() and old_record.exists():
                shutil.copy2(old_feature, feature_path)
                shutil.copy2(old_record, record_path)
        if feature_path.exists() and record_path.exists():
            cached = json.loads(record_path.read_text(encoding="utf-8"))
            feature = np.load(feature_path, allow_pickle=False)
            if (cached["feature_sha256"] == _digest(feature_path.read_bytes())
                    and feature.shape == (backbone.size,) and np.isfinite(feature).all()):
                record = cached["record"]
                record["capture_group"] = captures.get(path.resolve(), "")
                return record, feature, cached["baseline_prediction"]
        loaded = load_rgb_image(path, allowed_extensions=config.allowed_extensions, min_size=config.min_image_size)
        rgb = loaded.array
        gray = cv2.cvtColor(cv2.resize(rgb, (9, 8)), cv2.COLOR_RGB2GRAY)
        bits = gray[:, 1:] > gray[:, :-1]
        dhash = int.from_bytes(np.packbits(bits).tobytes(), "big")
        result = run_processing_pipeline(path, config, options)
        feature = backbone.extract(result.recognition_image)
        record = {
            "path": path.relative_to(source).as_posix(), "class_id": label,
            "sha256": original_hash,
            "decoded_sha256": _digest(str(rgb.shape).encode() + rgb.tobytes()),
            "dhash": f"{dhash:016x}", "capture_group": captures.get(path.resolve(), ""),
            "filter": result.metadata.get("filter", {}),
            "capture_quality": result.metadata.get("capture_quality", {}),
        }
        prediction = baseline.predict_image(result.recognition_image).top_class_id if baseline else ""
        np.save(feature_path, feature, allow_pickle=False)
        record_path.write_text(json.dumps({"record": record, "baseline_prediction": prediction,
                                          "feature_sha256": _digest(feature_path.read_bytes())}, ensure_ascii=False), encoding="utf-8")
        return record, feature, prediction

    with ThreadPoolExecutor(max_workers=4) as executor:
        for i, (record, feature, prediction) in enumerate(executor.map(extract, paths)):
            records.append(record)
            features.append(feature)
            baseline_predictions.append(prediction)
            if (i + 1) % 25 == 0:
                print(f"Prepared {i + 1}/{len(paths)} images", flush=True)
    groups = image_groups(records)
    labels = [row["class_id"] for row in records]
    splits = grouped_split(labels, groups, seed=config.random_seed)
    for row, group, split in zip(records, groups, splits, strict=True):
        row.update(group=group, split=split)
    (output / "dataset_manifest.json").write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    matrix, targets = np.vstack(features), np.asarray(labels)
    train = np.array(splits) == "train"
    validation = np.array(splits) == "validation"
    test = np.array(splits) == "test"
    training_sets = [("original", matrix[train], targets[train], np.asarray(groups)[train])]
    augmentation_records = []
    if args.augment:
        indices = training_indices(splits)

        def augment(index):
            label, path = paths[index]
            loaded = load_rgb_image(path, allowed_extensions=config.allowed_extensions, min_size=config.min_image_size)
            # Save losslessly, then use the exact application preparation on each variation.
            variants, evidence = [], []
            with tempfile.TemporaryDirectory(prefix="ecoscan_capture_") as temporary:
                working = prepare_working_image(loaded.array, config.processing.get("max_dimension", 640)).resized
                for name, image in capture_variants(working):
                    variant_path = Path(temporary) / f"{name}.png"
                    Image.fromarray(image).save(variant_path)
                    prepared = run_processing_pipeline(variant_path, config, options)
                    variants.append(backbone.extract(prepared.recognition_image))
                    evidence.append({"parent": records[index]["path"], "parent_sha256": records[index]["sha256"],
                                     "group": groups[index], "split": "train", "variant": name,
                                     "version": AUGMENTATION_VERSION, "filter": prepared.metadata["filter"]})
            return variants, [label] * len(variants), evidence

        extra_features, extra_labels = [], []
        with ThreadPoolExecutor(max_workers=4) as executor:
            for i, (variants, variant_labels, evidence) in enumerate(executor.map(augment, indices)):
                extra_features.extend(variants)
                extra_labels.extend(variant_labels)
                augmentation_records.extend(evidence)
                if (i + 1) % 25 == 0:
                    print(f"Augmented {i + 1}/{len(indices)} training originals", flush=True)
        training_sets.append(("capture_augmented", np.vstack([matrix[train], *extra_features]),
                              np.concatenate([targets[train], extra_labels]),
                              np.concatenate([np.asarray(groups)[train],
                                              [row["group"] for row in augmentation_records]])))
    (output / "augmentation_manifest.json").write_text(json.dumps(augmentation_records, indent=2), encoding="utf-8")
    candidates = []
    head_types = ("logistic", "svm_calibrated") if args.heads == "compare" else ("logistic",)
    for strategy, train_features, train_labels, train_groups in training_sets:
        for head_type in head_types:
            c_values = (0.01, 0.1, 1.0) if head_type == "logistic" else (0.1, 1.0, 10.0)
            for c_value in c_values:
                head = build_head(head_type, c_value, train_labels, train_groups, config.random_seed)
                head.fit(train_features, train_labels)
                score = f1_score(targets[validation], head.predict(matrix[validation]), average="macro")
                candidates.append((float(score), c_value, head, strategy, head_type))
                print(f"Validated {strategy}/{head_type} C={c_value}: macro-F1={score:.4f}", flush=True)
    score, c_value, head, strategy, head_type = max(candidates, key=lambda candidate: candidate[0])
    classes = [str(c) for c in head.classes_]
    validation_probabilities = head.predict_proba(matrix[validation])
    # Select rejection policy on validation only; test never changes parameters.
    policies = []
    for threshold in (0.5, 0.6, 0.7, 0.8, 0.9, 0.95):
        report = _report(targets[validation], validation_probabilities, classes, threshold)
        if report["accepted_count"] >= 20 and (report["accepted_accuracy"] or 0) >= 0.9:
            policies.append(report)
    threshold = max(policies, key=lambda report: report["coverage"])["threshold"] if policies else 0.95
    validation_report = _report(targets[validation], validation_probabilities, classes, threshold)
    test_probabilities = head.predict_proba(matrix[test])
    test_report = _report(targets[test], test_probabilities, classes, threshold)
    if baseline:
        test_report["legacy_on_same_prepared_test"] = classification_report(
            targets[test], np.array(baseline_predictions)[test], labels=classes, output_dict=True, zero_division=0
        )
        test_report["legacy_comparison_note"] = "Legacy model may have trained on these source images; comparison is diagnostic, not an independent experiment."
    model_path = output / "candidate.joblib"
    joblib.dump({"model_type": f"mobilenetv2_{args.representation}_{head_type}", "head_type": head_type,
                 "representation": args.representation, "head": head, "classes": classes,
                 "threshold": threshold, "backbone_sha256": BACKBONE_SHA256,
                 "processing": contract}, model_path)
    shutil.copy2(args.backbone, output / "mobilenetv2-12.onnx")
    write_model_contract(model_path, contract)
    summary = {
        "classes": classes, "source_counts": dict(Counter(labels)),
        "split_counts": {s: dict(Counter(targets[np.array(splits) == s])) for s in ("train", "validation", "test")},
        "split_policy": "stratified five group folds: three train, one validation, one test (~60/20/20)",
        "grouping": "decoded exact duplicates, dHash distance <=4, optional object/capture CSV",
        "capture_groups_provided": bool(args.groups), "unique_groups": len(set(groups)),
        "selection": {"C": c_value, "validation_macro_f1": score,
                      "strategy": strategy,
                      "head_type": head_type,
                      "candidates": [{"C": c, "validation_macro_f1": f, "strategy": s, "head_type": h}
                                     for f, c, _, s, h in candidates]},
        "augmentation": {"enabled": args.augment, "version": AUGMENTATION_VERSION,
                         "generated": len(augmentation_records), "split": "train_only"},
        "validation": validation_report, "test": test_report,
        "processing_options": asdict(options), "processing": contract,
        "backbone": {"source": BACKBONE_URL, "sha256": BACKBONE_SHA256,
                     "features": f"{backbone.size} frozen {args.representation}"},
        "manifest_sha256": _digest((output / "dataset_manifest.json").read_bytes()),
        "model_sha256": _digest(model_path.read_bytes()),
        "environment": {"python": platform.python_version(), "opencv": cv2.__version__, "sklearn": sklearn.__version__, "numpy": np.__version__},
        "active_model_changed": False,
        "promotion_status": "awaiting_new_group_photos_and_review",
        "limitations": ["Material cannot always be inferred from shape alone.",
                        "No detection boxes, object tracking or out-of-distribution guarantee.",
                        "Without capture groups, same physical objects may remain across sets.",
                        "Scores are not a calibrated probability of safe disposal."],
    }
    (output / "training_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    with (output / "test_predictions.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["path", "true_class", "predicted_class", "score", "accepted"])
        writer.writeheader()
        for row, probabilities in zip([row for row in records if row["split"] == "test"], test_probabilities, strict=True):
            writer.writerow({"path": row["path"], "true_class": row["class_id"],
                             "predicted_class": classes[int(probabilities.argmax())],
                             "score": float(probabilities.max()), "accepted": bool(probabilities.max() >= threshold)})
    print(json.dumps({"output": str(output), "test_accuracy": test_report["top1"]["accuracy"],
                      "test_macro_f1": test_report["top1"]["macro avg"]["f1-score"],
                      "coverage": test_report["coverage"], "accepted_accuracy": test_report["accepted_accuracy"]}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
