from __future__ import annotations

import json
from pathlib import Path

from ecoscan.services.model_evidence import evaluate_bundled_seed


ROOT = Path(__file__).resolve().parents[1]


def test_versioned_historical_evidence_matches_bundled_artifacts():
    actual = evaluate_bundled_seed(ROOT / "models" / "semantic-v1")
    recorded = json.loads(
        (ROOT / "docs" / "model_evaluation" / "semantic_v1_historical.json")
        .read_text(encoding="utf-8")
    )
    assert actual == recorded
    assert actual["independent_test"] is False
    assert actual["hash_intersections"] == {
        "train_validation": 0,
        "train_held_out": 0,
        "validation_held_out": 0,
    }
