from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.app.pipeline import ProcessingPipelineOptions, run_processing_pipeline
from ecoscan.config import load_config
from ecoscan.services.visual_report import save_pipeline_artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run EcoScan processing pipeline for one image.")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "processing_demo")
    parser.add_argument("--filter", default="auto")
    parser.add_argument("--segmentation", default="auto")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config()
    result = run_processing_pipeline(
        args.image,
        config,
        ProcessingPipelineOptions(
            filter_name=args.filter,
            segmentation_name=args.segmentation,
        ),
    )
    artifacts = save_pipeline_artifacts(result, args.output)
    print("EcoScan processing pipeline complete.")
    for path in artifacts:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
