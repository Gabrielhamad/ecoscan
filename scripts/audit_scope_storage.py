"""Inventory dataset storage without removing originals or changing splits."""
import json
from pathlib import Path


def audit(root: Path) -> dict:
    active = set(json.loads((root / "config/settings.json").read_text(encoding="utf-8"))["classes"])
    rows = []
    for split in ("raw", "curated", "processed", "train", "validation", "test"):
        for folder in sorted((root / "data" / split).glob("*")):
            if not folder.is_dir():
                continue
            files = [p for p in folder.rglob("*") if p.is_file() and not p.is_symlink()]
            rows.append({"split": split, "category": folder.name,
                         "in_scope": folder.name in active, "files": len(files),
                         "bytes": sum(p.stat().st_size for p in files)})
    return {"mode": "read_only", "rows": rows,
            "outside_scope_bytes": sum(r["bytes"] for r in rows if not r["in_scope"]),
            "warning": "Folder labels are not verified image labels. Preserve rejection examples and originals before cleanup."}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    report = root / "reports/scope_storage_audit.json"
    report.write_text(json.dumps(audit(root), indent=2), encoding="utf-8")
    print(report)
