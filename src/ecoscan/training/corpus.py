"""Build a private worker corpus from explicitly reviewed, grouped examples."""
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath

from PIL import Image, ImageOps


def build_corpus(manifest, source, output, classes):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Use a new output directory outside the image source")
    entries, files, hashes, pixels, groups = [], [], set(), set(), {}
    counts = {split: Counter() for split in ("train", "validation")}
    excluded = 0
    for row in manifest:
        if row.get("eligible_for_fit") is not True or row.get("split") == "test":
            excluded += 1
            continue
        if not row.get("review_method") or not row.get("item_id"):
            raise ValueError("Explicit object-level review is required")
        split, label, group = row["split"], row["class_id"], row.get("group")
        if split not in counts or label not in classes or not isinstance(group, str) or not group.strip():
            raise ValueError("Invalid split, class or capture group")
        if group in groups and groups[group] != split:
            raise ValueError("Capture group crosses train and validation")
        groups[group] = split
        relative = PurePosixPath(row["path"])
        path = (source / relative).resolve()
        if relative.is_absolute() or ".." in relative.parts or not path.is_relative_to(source):
            raise ValueError("Image escapes source directory")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != row["sha256"]:
            raise ValueError("Source image checksum mismatch")
        with Image.open(path) as image:
            rgb = ImageOps.exif_transpose(image).convert("RGB")
            decoded = hashlib.sha256(str(rgb.size).encode() + rgb.tobytes()).hexdigest()
        if digest in hashes or decoded in pixels:
            raise ValueError("Duplicate image in corpus")
        hashes.add(digest)
        pixels.add(decoded)
        key = f"corpus/{digest}{path.suffix.lower()}"
        entries.append({"key": key, "class": label, "split": split,
                        "group": group, "sha256": digest, "item_id": row["item_id"]})
        files.append((key, data))
        counts[split][label] += 1
    missing = {split: {label: max(0, 20 - counts[split][label]) for label in classes}
               for split in counts}
    report = {"ready": not any(n for split in missing.values() for n in split.values()),
              "counts": {split: {label: counts[split][label] for label in classes} for split in counts},
              "missing_to_minimum": missing, "excluded": excluded,
              "note": "Minimum counts do not certify accuracy or independent physical objects."}
    # Validate everything before creating the output; never overwrite a previous batch.
    output.mkdir(parents=True)
    for key, data in files:
        destination = output / key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    (output / "corpus.json").write_text(json.dumps({"bootstrap": True, "images": entries}, indent=2), encoding="utf-8")
    (output / "readiness.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
