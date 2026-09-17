from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.services.project_status import build_project_status, format_status_markdown


def main() -> int:
    config = load_config()
    items = build_project_status(config)
    output_path = config.directories["reports"] / "project_status.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = format_status_markdown(items)
    output_path.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nSaved: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

