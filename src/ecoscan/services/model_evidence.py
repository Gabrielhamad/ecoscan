"""Reproduce the historical metrics bundled with the semantic release."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import numpy as np

from ecoscan.classification.semantic_onnx import file_digest, softmax
from ecoscan.metrics.classification_metrics import classification_report


def evaluate_bundled_seed(model_dir: str | Path) -> dict:
    folder = Path(model_dir)
    metadata_path = folder / "semantic.json"
    head_path = folder / "head.npz"
    seed_path = folder / "learning_seed.npz"
    seed_metadata_path = folder / "learning_seed.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    seed_metadata = json.loads(seed_metadata_path.read_text(encoding="utf-8"))

    if file_digest(head_path) != metadata["head_sha256"]:
        raise ValueError("Bundled head hash does not match semantic metadata.")
    if file_digest(seed_path) != seed_metadata["sha256"]:
        raise ValueError("Bundled learning seed hash does not match its metadata.")
    if (seed_metadata["encoder_sha256"] != metadata["encoder_sha256"]
            or seed_metadata["processing"] != metadata["processing"]):
        raise ValueError("Model and seed use different encoder or processing contracts.")

    with np.load(head_path, allow_pickle=False) as head_data:
        arrays = {name: head_data[name].copy() for name in head_data.files}
    with np.load(seed_path, allow_pickle=False) as seed_data:
        train_labels = seed_data["train_y"].tolist()
        validation_labels = seed_data["validation_y"].tolist()
        validation_features = seed_data["validation_x"]

    classes = list(metadata["head_classes"])
    if (len(validation_features) != len(validation_labels)
            or set(train_labels) != set(classes)
            or set(validation_labels) != set(classes)):
        raise ValueError("Bundled seed labels or feature rows are inconsistent.")

    predictions = [_predict(feature, metadata, arrays) for feature in validation_features]
    top = [prediction[0] for prediction in predictions]
    accepted = [prediction[0] if prediction[1] else None for prediction in predictions]
    train_hashes = set(seed_metadata.get("training_hashes", []))
    validation_hashes = set(seed_metadata.get("validation_hashes", []))
    held_out_hashes = set(seed_metadata.get("held_out_hashes", []))
    accepted_total = sum(prediction[1] for prediction in predictions)
    accepted_correct = sum(prediction[1] and prediction[0] == expected
                           for prediction, expected in zip(predictions, validation_labels, strict=True))

    return {
        "schema_version": 1,
        "evaluation_kind": "historical_reused_features",
        "independent_test": False,
        "artifacts": {
            "semantic_sha256": file_digest(metadata_path),
            "head_sha256": metadata["head_sha256"],
            "seed_sha256": seed_metadata["sha256"],
            "encoder_sha256": metadata["encoder_sha256"],
            "processing_sha256": metadata["processing"]["sha256"],
        },
        "counts": {
            "train": dict(sorted(Counter(train_labels).items())),
            "validation": dict(sorted(Counter(validation_labels).items())),
            "held_out_hashes_without_features": len(held_out_hashes),
        },
        "hash_intersections": {
            "train_validation": len(train_hashes & validation_hashes),
            "train_held_out": len(train_hashes & held_out_hashes),
            "validation_held_out": len(validation_hashes & held_out_hashes),
        },
        "top1": classification_report(validation_labels, top, classes),
        "accepted": classification_report(validation_labels, accepted, classes),
        "acceptance": {
            "threshold": metadata["threshold"],
            "accepted": accepted_total,
            "correct": accepted_correct,
            "wrong": accepted_total - accepted_correct,
            "rejected": len(validation_labels) - accepted_total,
        },
        "limitations": [
            "The same historical validation features were used during model development.",
            "Original images and object/session groups are not bundled, so scene leakage cannot be re-audited.",
            "Held-out hashes have no bundled labels or features and cannot be scored from this repository.",
            "These metrics do not measure new mobile photos or out-of-scope rejection.",
        ],
    }


def _predict(feature, metadata, arrays) -> tuple[str, bool]:
    prior = softmax(arrays["logit_scale"] * feature @ arrays["prototypes"].T)
    probe = softmax(((feature - arrays["mean"]) / arrays["scale"])
                    @ arrays["coef"].T + arrays["intercept"])
    all_classes = list(metadata["classes"])
    aligned = np.zeros(len(all_classes))
    for index, label in enumerate(metadata["head_classes"]):
        aligned[all_classes.index(label)] = probe[index]
    scores = metadata["prior_weight"] * prior + (1 - metadata["prior_weight"]) * aligned
    if not np.isfinite(scores).all() or not np.isclose(scores.sum(), 1):
        raise ValueError("Historical evaluation produced invalid semantic scores.")
    label = all_classes[int(scores.argmax())]
    accepted = label != "unknown" and float(scores.max()) >= float(metadata["threshold"])
    return label, accepted
