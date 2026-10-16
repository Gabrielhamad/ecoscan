"""Keep exact copies, visual near-copies and declared capture groups together."""
from __future__ import annotations

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold


def image_groups(records: list[dict], *, max_hamming: int = 4) -> list[int]:
    parents = list(range(len(records)))

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    decoded_labels = {}
    for i, record in enumerate(records):
        digest = record["decoded_sha256"]
        if digest in decoded_labels and decoded_labels[digest] != record["class_id"]:
            raise ValueError("Identical images have conflicting labels; review the dataset.")
        decoded_labels[digest] = record["class_id"]
        for j in range(i):
            other = records[j]
            same_capture = record.get("capture_group") and record["capture_group"] == other.get("capture_group")
            same_image = digest == other["decoded_sha256"]
            near_copy = (int(record["dhash"], 16) ^ int(other["dhash"], 16)).bit_count() <= max_hamming
            if same_capture or same_image or near_copy:
                parents[root(i)] = root(j)
    return [root(i) for i in range(len(records))]


def grouped_split(labels: list[str], groups: list[int], *, seed: int = 42) -> list[str]:
    if len(labels) != len(groups) or not labels:
        raise ValueError("Labels and groups must be nonempty and aligned.")
    for label in set(labels):
        if len({g for y, g in zip(labels, groups, strict=True) if y == label}) < 5:
            raise ValueError(f"At least five independent image groups are required for {label}.")
    folds = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    assigned = ["train"] * len(labels)
    for fold, (_, indices) in enumerate(folds.split(np.zeros(len(labels)), labels, groups)):
        split = "test" if fold == 0 else "validation" if fold == 1 else "train"
        for index in indices:
            assigned[index] = split
    for split in ("train", "validation", "test"):
        if {label for label, s in zip(labels, assigned, strict=True) if s == split} != set(labels):
            raise ValueError(f"{split} is missing a class. Collect more independent groups.")
    return assigned
