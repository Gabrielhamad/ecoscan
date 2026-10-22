"""Scheduled private training worker. Reviewed photos are never public artifacts."""
from collections import Counter
import hashlib
import io
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import numpy as np
from PIL import Image

from ecoscan.app.pipeline import run_processing_pipeline
from ecoscan.classification.visual_features import VisualFeatureConfig, extract_visual_features
from ecoscan.classification.visual_svm import VisualSvmClassifier
from ecoscan.image_processing.contracts import processing_contract, write_model_contract, contract_path
from ecoscan.metrics.classification_metrics import classification_report


BUCKET = "ecoscan-training"


def eligible(rows, classes):
    return [r for r in rows if r.get("status") == "approved"
            and r.get("consent") is True and r.get("expected_class") in classes]


def gate(candidate, reference, classes):
    """Use accepted predictions: rejection counts as a miss, not a correct answer."""
    def valid(report):
        try:
            values = [report["macro_f1"]]
            for label in classes:
                score = report["by_class"][label]
                support = score["support"]
                if isinstance(support, bool) or not isinstance(support, int) or support < 20:
                    return False
                values.extend((score["precision"], score["recall"]))
            return all(not isinstance(value, bool) and math.isfinite(value)
                       and 0 <= value <= 1 for value in values)
        except (KeyError, TypeError, ValueError):
            return False

    if not valid(candidate) or (reference is not None and not valid(reference)):
        return False
    if candidate["macro_f1"] < 0.85:
        return False
    for label in classes:
        score = candidate["by_class"][label]
        if score["support"] < 20 or min(score["precision"], score["recall"]) < 0.80:
            return False
        if reference and score["recall"] < reference["by_class"][label]["recall"]:
            return False
    return reference is None or candidate["macro_f1"] >= reference["macro_f1"] + 0.01


def update_rows(store, rows, state, run_id):
    for row in rows:
        previous = row.get("revision", 0)
        new = dict(row, revision=previous + 1, training_status=state, candidate_id=run_id)
        saved = store.save(new, previous_revision=previous)
        row.update(saved)


def prepare_samples(config, samples, root, feature_config):
    features, labels = [], []
    for index, (data, label) in enumerate(samples):
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        path = root / f"{index}.jpg"
        path.write_bytes(data)
        prepared = run_processing_pipeline(path, config).recognition_image
        features.append(extract_visual_features(prepared, feature_config))
        labels.append(label)
    return np.vstack(features), labels


def evaluate(model, features, labels, classes):
    predictions = [model.predict_feature(row[None, :]).class_id for row in features]
    return classification_report(labels, predictions, list(classes))


def run(config, store):
    rows = eligible(store.list(), config.classes)
    if not any(r.get("training_status") in ("queued", "waiting_dataset", "failed", "training", "validating") for r in rows):
        return "idle"
    run_id = uuid4().hex
    bucket = store.client.storage.from_(BUCKET)
    try:
        # Only an explicit missing object means missing data; provider failures fail the run.
        try:
            corpus_data = bucket.download("corpus.json")
        except Exception as error:
            status = getattr(error, "status", None) or getattr(error, "status_code", None)
            code = getattr(error, "code", None)
            if str(status) == "404" or code in ("NoSuchKey", "not_found"):
                update_rows(store, rows, "waiting_dataset", run_id)
                return "waiting_dataset"
            raise
        corpus = json.loads(corpus_data)
        samples = {"train": [], "validation": []}
        hashes, groups = {}, {}
        for item in corpus["images"]:
            split, label, key = item["split"], item["class"], item["key"]
            if split not in samples or label not in config.classes or not key.startswith("corpus/") or ".." in key:
                raise ValueError("Invalid corpus manifest")
            group = item["group"]
            if not isinstance(group, str) or not group.strip():
                raise ValueError("Missing capture group")
            if group in groups and groups[group] != split:
                raise ValueError("Object group crosses train/validation")
            groups[group] = split
            data = bucket.download(key)
            digest = hashlib.sha256(data).hexdigest()
            if digest != item["sha256"] or digest in hashes:
                raise ValueError("Corpus integrity or duplication error")
            hashes[digest] = (split, label)
            samples[split].append((data, label))
        for row in rows:
            data = store.image(row)
            digest = hashlib.sha256(data).hexdigest()
            previous = hashes.get(digest)
            if previous:
                if previous != ("train", row["expected_class"]):
                    raise ValueError("Correction conflicts with fixed corpus")
                continue
            hashes[digest] = ("train", row["expected_class"])
            samples["train"].append((data, row["expected_class"]))
        for split, minimum in (("train", 20), ("validation", 20)):
            counts = Counter(label for _, label in samples[split])
            if any(counts[label] < minimum for label in config.classes):
                update_rows(store, rows, "waiting_dataset", run_id)
                return "waiting_dataset"
        update_rows(store, rows, "training", run_id)
        with TemporaryDirectory(prefix="recicla-training-") as temporary:
            root = Path(temporary)
            feature_config = VisualFeatureConfig()
            train_x, train_y = prepare_samples(config, samples["train"], root, feature_config)
            valid_x, valid_y = prepare_samples(config, samples["validation"], root, feature_config)
            model = VisualSvmClassifier.fit(train_x, train_y, feature_config=feature_config,
                                           threshold=config.confidence_threshold,
                                           notes=["Automatic reviewed batch " + run_id])
            model_path = root / "model.joblib"
            model.save(model_path)
            write_model_contract(model_path, processing_contract(config))
            update_rows(store, rows, "validating", run_id)
            metrics = evaluate(model, valid_x, valid_y, config.classes)
            reference = None
            # Compare against the active remote artifact on the SAME validation data.
            # A missing pointer is explicitly represented by corpus.bootstrap=true.
            active_exists = any(entry.get("name") == "active.json" for entry in bucket.list())
            if active_exists or not corpus.get("bootstrap", False):
                active = json.loads(bucket.download("active.json"))
                old_bytes = bucket.download(active["model_key"])
                if hashlib.sha256(old_bytes).hexdigest() != active["sha256"]:
                    raise ValueError("Active model checksum mismatch")
                old_path = root / "reference.joblib"
                old_path.write_bytes(old_bytes)
                old = VisualSvmClassifier.load(old_path)
                old_x, old_y = prepare_samples(config, samples["validation"], root, old.metadata.feature_config)
                reference = evaluate(old, old_x, old_y, config.classes)
            passed = gate(metrics, reference, config.classes)
            current = {r["id"]: r for r in store.list()}
            if any(current.get(r["id"], {}).get("revision") != r["revision"] for r in rows):
                raise ValueError("Review changed during training")
            prefix = f"runs/{run_id}"
            for name, data in (("model.joblib", model_path.read_bytes()),
                               ("contract.json", contract_path(model_path).read_bytes()),
                               ("metrics.json", json.dumps({"candidate": metrics, "reference": reference}).encode())):
                bucket.upload(f"{prefix}/{name}", data, file_options={"content-type": "application/octet-stream"})
            if passed:
                release = {"id": run_id, "model_key": f"{prefix}/model.joblib",
                           "contract_key": f"{prefix}/contract.json",
                           "sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
                           "processing_sha256": processing_contract(config)["sha256"],
                           "reviews": {r["id"]: {"reviewed_at": r.get("reviewed_at"),
                                        "expected_class": r["expected_class"]} for r in rows},
                           "classes": list(config.classes)}
                bucket.upload("active.json", json.dumps(release).encode(),
                              file_options={"upsert": "true", "content-type": "application/json"})
            state = "published" if passed else "validation_failed"
            update_rows(store, rows, state, run_id)
            return state
    except Exception:
        # Do not expose provider errors, image paths, credentials or personal records.
        try:
            update_rows(store, rows, "failed", run_id)
        except Exception:
            pass
        raise RuntimeError("Training batch failed; active artifact was not intentionally replaced.") from None
