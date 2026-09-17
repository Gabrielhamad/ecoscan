from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.services.aps_audit import build_aps_audit, format_audit_markdown, write_aps_audit_report


def main() -> int:
    config = load_config()
    items = build_aps_audit(config)
    written = write_aps_audit_report(config)
    print(format_audit_markdown(items))
    print(f"JSON: {written['json']}")
    print(f"Markdown: {written['markdown']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
