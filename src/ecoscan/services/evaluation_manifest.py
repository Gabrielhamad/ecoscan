"""Validation of image manifests before model evaluation.

This audits declared splits, file names, hashes, and optional object/session groups.
Passing does not independently establish provenance or real-world accuracy.
"""
from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath
import re
from typing import Collection


_SPLITS = frozenset({"train", "validation", "test"})
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def audit_evaluation_manifest(
    records: object,
    *,
    allowed_classes: Collection[str],
    require_groups: bool = False,
    development_hashes: Collection[str] = (),
) -> dict:
    """Reject duplicate images, unsafe paths, and known split leakage.

    `require_groups` checks object/session separation *within the supplied
    manifest*. Historical training material not supplied here cannot be audited.
    """
    if not isinstance(records, list) or not records:
        raise ValueError("Manifest must contain a nonempty JSON list")

    allowed = set(allowed_classes)
    seen_paths: set[str] = set()
    seen_hashes: set[str] = set()
    split_groups: dict[str, dict[str, set[str]]] = {
        name: {} for name in ("object_id", "session_id")
    }
    classes: Counter[str] = Counter()
    splits: Counter[str] = Counter()

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Invalid manifest entry {index}")
        split = record.get("split")
        class_id = record.get("class_id")
        path = record.get("path")
        digest = record.get("sha256")
        if split not in _SPLITS:
            raise ValueError(f"Invalid split at entry {index}")
        if not isinstance(class_id, str) or class_id not in allowed:
            raise ValueError(f"Unsupported class at entry {index}")
        if not isinstance(path, str) or not path or "\\" in path:
            raise ValueError(f"Invalid relative path at entry {index}")
        parsed = PurePosixPath(path)
        if parsed.is_absolute() or any(part in {".", ".."} for part in path.split("/")) or ":" in path:
            raise ValueError(f"Unsafe image path at entry {index}")
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            raise ValueError(f"Invalid SHA-256 at entry {index}")
        if path in seen_paths or digest in seen_hashes:
            raise ValueError(f"Repeated file or image hash at entry {index}")
        seen_paths.add(path)
        seen_hashes.add(digest)
        splits[split] += 1
        if split == "test":
            classes[class_id] += 1

        if require_groups:
            for field, groups in split_groups.items():
                value = record.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"Missing {field} at entry {index}")
                groups.setdefault(value.strip(), set()).add(split)

    if not splits["test"]:
        raise ValueError("Manifest contains no test images")

    if require_groups:
        for field, groups in split_groups.items():
            if any(len(group_splits) > 1 for group_splits in groups.values()):
                raise ValueError(f"{field} crosses train/validation/test splits")

    reference_hashes = set(development_hashes)
    if not all(isinstance(value, str) and _SHA256.fullmatch(value) for value in reference_hashes):
        raise ValueError("Invalid development SHA-256")
    test_hashes = {row["sha256"] for row in records if row["split"] == "test"}
    if test_hashes.intersection(reference_hashes):
        raise ValueError("Test images overlap the supplied development hashes")

    return {
        "records": len(records),
        "test_count": splits["test"],
        "test_support": dict(sorted(classes.items())),
        "split_counts": dict(sorted(splits.items())),
        "object_session_separation_checked": require_groups,
        "development_hashes_checked": len(reference_hashes),
        "independent_test_confirmed": False,
    }
