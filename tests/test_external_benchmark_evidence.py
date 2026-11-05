from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_trashnet_diagnostic_evidence_is_internally_consistent():
    folder = ROOT / "docs" / "model_evaluation"
    report = json.loads((folder / "trashnet_priority_diagnostic.json").read_text())
    manifest_path = folder / "trashnet_priority_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    evaluation = report["evaluation"]

    assert report["independent_test"] is False
    assert report["selection"]["records"] == len(manifest) == 224
    assert report["selection"]["counts"] == dict(Counter(
        row["class_id"] for row in manifest
    ))
    assert report["selection"]["manifest"] == hashlib.sha256(
        manifest_path.read_bytes().rstrip(b"\n")
    ).hexdigest()
    assert evaluation["evaluation_classes"] == ["plastic", "metal", "glass"]
    assert evaluation["top1"]["total"] == 224
    assert evaluation["acceptance"] == {
        "threshold": 0.8,
        "accepted": 94,
        "correct": 94,
        "wrong": 0,
        "rejected": 130,
    }
