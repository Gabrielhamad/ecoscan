from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.image_processing.adaptive_filters import apply_adaptive_filter_pipeline
from ecoscan.image_processing.filters import apply_filter
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.image_processing.preprocessing import resize_image
from ecoscan.image_processing.quality import analyze_image_quality
from ecoscan.segmentation.adaptive import segment_image_adaptive
from ecoscan.segmentation.methods import SegmentationUnavailableError, segment_image
from ecoscan.services.visual_report import save_segmentation_comparison


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare EcoScan segmentation methods side by side.")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "segmentation_experiments")
    parser.add_argument("--filter", default="gaussian")
    parser.add_argument("--methods", nargs="+", default=["auto", "none", "otsu", "hsv_color", "grabcut"])
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
    requested_filter = args.filter.lower().strip()
    if requested_filter == "auto":
        adaptive_filter = apply_adaptive_filter_pipeline(image, config.filters, quality=analyze_image_quality(image))
        filtered = adaptive_filter.filter_result.image
    else:
        selected_filter = requested_filter
        filter_params = dict(config.filters.get(selected_filter, {}))
        filtered = apply_filter(image, selected_filter, filter_params).image

    results = []
    skipped = []
    adaptive_decisions = []
    for method in args.methods:
        params = dict(config.segmentation.get(method, {}))
        try:
            if method == "auto":
                adaptive = segment_image_adaptive(filtered, params, quality=analyze_image_quality(filtered))
                adaptive_decisions.append(adaptive.decision)
                results.append(
                    replace(
                        adaptive.segmentation,
                        name=f"auto -> {adaptive.segmentation.name}",
                        parameters={**adaptive.segmentation.parameters, "decision": adaptive.decision},
                    )
                )
            else:
                results.append(segment_image(filtered, method, params))
        except SegmentationUnavailableError as exc:
            skipped.append({"method": method, "reason": str(exc)})

    artifacts = save_segmentation_comparison(results, filtered, args.output)
    skipped_path = Path(args.output) / "skipped_segmentation_methods.json"
    skipped_path.write_text(json.dumps(skipped, indent=2, ensure_ascii=False), encoding="utf-8")
    artifacts.append(skipped_path)
    if adaptive_decisions:
        decisions_path = Path(args.output) / "adaptive_segmentation_decision.json"
        decisions_path.write_text(json.dumps(adaptive_decisions, indent=2, ensure_ascii=False), encoding="utf-8")
        artifacts.append(decisions_path)

    print("EcoScan segmentation comparison complete.")
    if skipped:
        print("Skipped methods:")
        for item in skipped:
            print(f"- {item['method']}: {item['reason']}")
    for path in artifacts:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
