"""Combine a fixed reference and reviewed additions without modifying either."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil


def stage(reference, source, additions, extra_source, output):
    output, source, extra_source = map(lambda p: Path(p).resolve(), (output, source, extra_source))
    if output.exists() or any(output.is_relative_to(root) or root.is_relative_to(output)
                              for root in (source, extra_source)):
        raise ValueError("Use a new isolated output")
    files, seen, groups = [], set(), []
    for root, rows, extra in ((source, reference, False), (extra_source, additions, True)):
        for row in rows:
            if extra and (row.get("eligible_for_fit") is not True or row.get("split") != "train"
                          or not row.get("review_method") or not row.get("item_id")):
                raise ValueError("Additions must be reviewed training objects")
            path = (root / row["path"]).resolve()
            if not path.is_relative_to(root) or Path(row["path"]).is_absolute():
                raise ValueError("Invalid source path")
            if row["path"] in seen or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
                raise ValueError("Duplicate path or changed image")
            seen.add(row["path"])
            group = row.get("group")
            if group is None or str(group).strip() == "":
                raise ValueError("Capture group required")
            files.append((path, row["path"]))
            groups.append({"path": row["path"], "group_id": ("addition:" if extra else "reference:") + str(group)})
    output.mkdir(parents=True)
    for path, relative in files:
        destination = output / "images" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    with (output / "groups.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["path", "group_id"])
        writer.writeheader()
        writer.writerows(groups)
    print(json.dumps({"reference_images": len(reference), "reviewed_additions": len(additions),
                      "output": str(output)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reference", "source", "additions", "extra-source", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    stage(json.loads(args.reference.read_text(encoding="utf-8")), args.source,
          json.loads(args.additions.read_text(encoding="utf-8")), args.extra_source, args.output)
