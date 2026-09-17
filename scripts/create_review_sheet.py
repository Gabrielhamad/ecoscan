from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.services.dataset_review import create_review_sheet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a CSV review sheet for EcoScan dataset curation.")
    parser.add_argument("--dataset", type=Path, default=None, help="Defaults to data/raw.")
    parser.add_argument("--output", type=Path, default=None, help="Defaults to reports/dataset_review/review_sheet.csv.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    output = create_review_sheet(config, dataset_dir=args.dataset, output_path=args.output)
    print(f"Review sheet created: {output}")
    print("Use status=accepted/rejected and suggested_class to correct labels before training.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

