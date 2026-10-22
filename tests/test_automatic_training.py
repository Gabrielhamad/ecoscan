from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch
import hashlib
import json
import numpy as np
import pytest

from ecoscan.training.automatic import eligible, gate, run


def metrics():
    return {"macro_f1": .90, "by_class": {
        "plastic": {"support": 20, "precision": .9, "recall": .9},
        "metal": {"support": 20, "precision": .9, "recall": .9}}}


def test_gate_rejects_regression_and_missing_support():
    good = metrics()
    assert gate(good, None, ["plastic", "metal"])
    assert not gate(good, good, ["plastic", "metal"])
    bad = deepcopy(good)
    bad["by_class"]["plastic"]["support"] = 1
    assert not gate(bad, None, ["plastic", "metal"])
    bad = deepcopy(good)
    bad["by_class"]["metal"]["precision"] = .79
    assert not gate(bad, None, ["plastic", "metal"])


def test_only_consenting_approved_rows_are_eligible():
    rows = [{"status": "approved", "consent": True, "expected_class": "plastic"},
            {"status": "pending", "consent": True, "expected_class": "plastic"},
            {"status": "approved", "consent": False, "expected_class": "plastic"}]
    assert eligible(rows, ["plastic"]) == rows[:1]


def test_missing_corpus_records_wait_without_training():
    store = MagicMock()
    row = {"id": "test", "status": "approved", "consent": True,
           "expected_class": "plastic", "revision": 2, "training_status": "queued"}
    store.list.return_value = [row]
    missing = OSError()
    missing.status = 404
    store.client.storage.from_.return_value.download.side_effect = missing
    store.save.side_effect = lambda record, **kwargs: record
    assert run(SimpleNamespace(classes=["plastic"]), store) == "waiting_dataset"
    assert row["training_status"] == "waiting_dataset"
    store.client.storage.from_.return_value.upload.assert_not_called()


def test_idle_worker_has_no_external_writes():
    store = MagicMock()
    store.list.return_value = []
    assert run(SimpleNamespace(classes=["plastic"]), store) == "idle"
    store.save.assert_not_called()


@pytest.mark.parametrize("accepted", [True, False])
def test_full_worker_trains_validates_and_publishes(tmp_path, accepted):
    classes = ["plastic", "metal"]
    store = MagicMock()
    row = {"id": "review", "status": "approved", "consent": True,
           "expected_class": "plastic", "revision": 2, "training_status": "queued"}
    store.list.side_effect = lambda: [dict(row)]
    def save(record, **kwargs):
        row.update(record)
        return dict(row)
    store.save.side_effect = save
    store.image.return_value = b"new-photo"
    corpus = {"bootstrap": True, "images": []}
    objects = {}
    for split in ("train", "validation"):
        for category in classes:
            for index in range(20):
                key = f"corpus/{split}/{category}/{index}.jpg"
                data = key.encode()
                objects[key] = data
                corpus["images"].append({"key": key, "split": split, "class": category,
                                         "group": key, "sha256": hashlib.sha256(data).hexdigest()})
    objects["corpus.json"] = json.dumps(corpus).encode()
    bucket = store.client.storage.from_.return_value
    bucket.download.side_effect = lambda key: objects[key]
    bucket.list.return_value = []
    model = MagicMock()
    model.save.side_effect = lambda path: path.write_bytes(b"model")
    config = SimpleNamespace(classes=classes, confidence_threshold=.7)
    candidate_metrics = metrics()
    if not accepted:
        candidate_metrics["macro_f1"] = .40
    def features(config, samples, root, options):
        return np.zeros((len(samples), 2)), [label for _, label in samples]
    with patch("ecoscan.training.automatic.prepare_samples", side_effect=features), \
         patch("ecoscan.training.automatic.VisualSvmClassifier.fit", return_value=model), \
         patch("ecoscan.training.automatic.processing_contract", return_value={"sha256": "contract"}), \
         patch("ecoscan.training.automatic.evaluate", return_value=candidate_metrics):
        expected = "published" if accepted else "validation_failed"
        assert run(config, store) == expected
    assert row["training_status"] == expected
    keys = [call.args[0] for call in bucket.upload.call_args_list]
    assert ("active.json" in keys) is accepted
    assert len(keys) == (4 if accepted else 3)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 2, None, True])
def test_gate_rejects_invalid_metrics(value):
    bad = metrics()
    bad["by_class"]["plastic"]["precision"] = value
    assert not gate(bad, None, ["plastic", "metal"])
    assert not gate(metrics(), bad, ["plastic", "metal"])


@pytest.mark.parametrize("failure", [OSError("private provider details"), ValueError("invalid json")])
def test_provider_errors_are_failed_not_missing_data(failure):
    store = MagicMock()
    row = {"id": "test", "status": "approved", "consent": True,
           "expected_class": "plastic", "revision": 2, "training_status": "queued"}
    store.list.return_value = [row]
    store.save.side_effect = lambda record, **kwargs: record
    store.client.storage.from_.return_value.download.side_effect = failure
    with pytest.raises(RuntimeError, match="Training batch failed") as error:
        run(SimpleNamespace(classes=["plastic"]), store)
    assert "private provider details" not in str(error.value)
    assert row["training_status"] == "failed"
    store.client.storage.from_.return_value.upload.assert_not_called()
