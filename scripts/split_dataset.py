from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.services.dataset_split import split_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Split EcoScan raw dataset into train/validation/test.")
    parser.add_argument("--source", type=Path, default=None, help="Dataset source directory. Defaults to data/raw.")
    parser.add_argument("--overwrite", action="store_true", help="Clear existing split files inside data/train, data/validation and data/test.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    records = split_dataset(config, source_dir=args.source, overwrite=args.overwrite)

    counts = Counter((record.split, record.class_id) for record in records)
    print("EcoScan dataset split complete.")
    for split in ["train", "validation", "test"]:
        split_total = sum(count for (record_split, _), count in counts.items() if record_split == split)
        print(f"{split}: {split_total}")
        for class_id in config.classes:
            print(f"  {class_id}: {counts[(split, class_id)]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
