from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.image_processing.adaptive_filters import apply_adaptive_filter_pipeline
from ecoscan.image_processing.filters import FilterUnavailableError, apply_filter
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.image_processing.preprocessing import resize_image
from ecoscan.image_processing.quality import analyze_image_quality
from ecoscan.services.visual_report import save_filter_comparison


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare EcoScan filters side by side.")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "filter_experiments")
    parser.add_argument(
        "--filters",
        nargs="+",
        default=["auto", "none", "gaussian", "median", "bilateral", "clahe", "sobel", "canny"],
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config()
    loaded = load_rgb_image(
        args.image,
        allowed_extensions=config.allowed_extensions,
        min_size=config.min_image_size,
    )
    image = resize_image(loaded.array, config.image_size)

    results = []
    skipped = []
    adaptive_decisions = []
    for filter_name in args.filters:
        params = dict(config.filters.get(filter_name, {}))
        try:
            if filter_name == "auto":
                adaptive = apply_adaptive_filter_pipeline(image, config.filters, quality=analyze_image_quality(image))
                adaptive_decisions.append(adaptive.decision)
                results.append(adaptive.filter_result)
            else:
                results.append(apply_filter(image, filter_name, params))
        except FilterUnavailableError as exc:
            skipped.append({"filter": filter_name, "reason": str(exc)})

    artifacts = save_filter_comparison(results, image, args.output)
    skipped_path = Path(args.output) / "skipped_filters.json"
    skipped_path.write_text(json.dumps(skipped, indent=2, ensure_ascii=False), encoding="utf-8")
    artifacts.append(skipped_path)
    if adaptive_decisions:
        decision_path = Path(args.output) / "adaptive_filter_decision.json"
        decision_path.write_text(json.dumps(adaptive_decisions, indent=2, ensure_ascii=False), encoding="utf-8")
        artifacts.append(decision_path)

    print("EcoScan filter comparison complete.")
    if skipped:
        print("Skipped filters:")
        for item in skipped:
            print(f"- {item['filter']}: {item['reason']}")
    for path in artifacts:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
