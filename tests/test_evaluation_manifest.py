"""Regression tests for manifest provenance and leakage gates."""
from __future__ import annotations

from copy import deepcopy

import pytest

from ecoscan.services.evaluation_manifest import audit_evaluation_manifest


def _manifest():
    return [
        {"path": "plastic/p1.jpg", "sha256": "a" * 64, "class_id": "plastic",
         "split": "train", "object_id": "obj-1", "session_id": "session-1"},
        {"path": "plastic/p2.jpg", "sha256": "b" * 64, "class_id": "plastic",
         "split": "validation", "object_id": "obj-2", "session_id": "session-2"},
        {"path": "metal/m1.jpg", "sha256": "c" * 64, "class_id": "metal",
         "split": "test", "object_id": "obj-3", "session_id": "session-3"},
    ]


def _audit(rows, **kwargs):
    return audit_evaluation_manifest(
        rows, allowed_classes={"plastic", "metal", "glass"}, **kwargs
    )


def test_strict_manifest_reports_counts_without_claiming_independence():
    result = _audit(_manifest(), require_groups=True, development_hashes=["d" * 64])
    assert result["test_support"] == {"metal": 1}
    assert result["object_session_separation_checked"] is True
    assert result["development_hashes_checked"] == 1
    assert result["independent_test_confirmed"] is False


@pytest.mark.parametrize("path", ["../private.jpg", "/tmp/test.jpg", "x/../secret.jpg",
                                   r"C:\\secret.jpg", "", "./x.jpg"])
def test_manifest_refuses_unsafe_paths(path):
    rows = _manifest()
    rows[-1]["path"] = path
    with pytest.raises(ValueError, match="path"):
        _audit(rows)


def test_manifest_refuses_duplicate_image_hash_even_if_renamed():
    rows = _manifest()
    rows[-1]["sha256"] = rows[0]["sha256"]
    with pytest.raises(ValueError, match="Repeated"):
        _audit(rows)


@pytest.mark.parametrize("group", ["object_id", "session_id"])
def test_strict_manifest_rejects_groups_leaking_across_splits(group):
    rows = _manifest()
    rows[-1][group] = rows[0][group]
    with pytest.raises(ValueError, match=group):
        _audit(rows, require_groups=True)


def test_strict_manifest_requires_provenance_fields():
    rows = _manifest()
    del rows[-1]["session_id"]
    with pytest.raises(ValueError, match="session_id"):
        _audit(rows, require_groups=True)


def test_manifest_refuses_known_training_overlap():
    with pytest.raises(ValueError, match="overlap"):
        _audit(_manifest(), development_hashes=["c" * 64])


def test_missing_or_invalid_test_rows_are_rejected():
    rows = deepcopy(_manifest())
    rows[-1]["split"] = "training"
    with pytest.raises(ValueError, match="split"):
        _audit(rows)
    rows[-1]["split"] = "train"
    with pytest.raises(ValueError, match="no test images"):
        _audit(rows)
