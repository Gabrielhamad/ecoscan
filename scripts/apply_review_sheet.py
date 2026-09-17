from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.services.dataset_review import apply_review_sheet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply an EcoScan review sheet and build data/curated.")
    parser.add_argument("--review", type=Path, default=PROJECT_ROOT / "reports" / "dataset_review" / "review_sheet.csv")
    parser.add_argument("--source", type=Path, default=None, help="Defaults to data/raw.")
    parser.add_argument("--output", type=Path, default=None, help="Defaults to data/curated.")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    counts = apply_review_sheet(
        config,
        review_path=args.review,
        source_dir=args.source,
        output_dir=args.output,
        overwrite=args.overwrite,
    )
    print("Review sheet applied.")
    for key, value in counts.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

