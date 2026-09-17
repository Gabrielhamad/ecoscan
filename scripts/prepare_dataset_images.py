from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.services.dataset_preparation import prepare_dataset_images


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare EcoScan raw images for recognition.")
    parser.add_argument("--source", type=Path, default=None, help="Defaults to data/raw.")
    parser.add_argument("--output", type=Path, default=None, help="Defaults to data/processed.")
    parser.add_argument("--report-dir", type=Path, default=None, help="Defaults to reports/dataset_preparation.")
    parser.add_argument("--overwrite", action="store_true", help="Clear output directory before saving processed images.")
    parser.add_argument("--min-quality-score", type=int, default=55)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    summary, _ = prepare_dataset_images(
        config,
        source_dir=args.source,
        output_dir=args.output,
        report_dir=args.report_dir,
        overwrite=args.overwrite,
        min_quality_score=args.min_quality_score,
    )

    print("EcoScan dataset preparation complete.")
    print(f"Seen: {summary.total_seen}")
    print(f"Prepared: {summary.prepared}")
    print(f"Rejected: {summary.rejected}")
    print(f"Errors: {summary.errors}")
    for class_id in config.classes:
        print(f"  {class_id}: {summary.counts_by_class[class_id]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
