from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.app.pipeline import ProcessingPipelineOptions
from ecoscan.config import load_config
from ecoscan.disposal.impact import get_environmental_impact, load_environmental_impacts
from ecoscan.errors import format_console_error
from ecoscan.services.analysis_service import analyze_waste_image
from ecoscan.services.history import append_history_entry, build_history_entry, history_path_from_config
from ecoscan.services.visual_report import save_pipeline_artifacts
from ecoscan.utils.logging_config import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run EcoScan inference for one image.")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=None, help="Defaults to the best available EcoScan model.")
    parser.add_argument("--filter", default="auto")
    parser.add_argument("--segmentation", default="auto")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "inference_demo")
    parser.add_argument("--save-history", action="store_true", help="Save metadata only to logs/history.jsonl.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config()
        configure_logging(config.directories["logs"], include_stream=False)
        result = analyze_waste_image(
            args.image,
            config,
            options=ProcessingPipelineOptions(filter_name=args.filter, segmentation_name=args.segmentation),
            model_path=args.model,
        )
        save_pipeline_artifacts(result.pipeline, args.output)

        print("EcoScan inference complete.")
        print(f"Model type: {result.model_type}")
        print(f"Top class: {result.top_class}")
        print(f"Accepted class: {result.predicted_class or '__uncertain__'}")
        print(f"Predicted probability/score: {result.probability:.3f}" if result.probability is not None else "Predicted probability/score: unavailable")
        filter_decision = result.pipeline.metadata["filter"]["decision"]
        segmentation_decision = result.pipeline.metadata["segmentation"]["decision"]
        capture_quality = result.pipeline.metadata.get("capture_quality", {})
        print(f"Filter used: {filter_decision.get('selected', result.pipeline.metadata['filter']['name'])}")
        print(f"Segmentation used: {segmentation_decision.get('selected', result.pipeline.metadata['segmentation']['name'])}")
        print(f"Visual elements: {result.pipeline.element_analysis.significant_count}")
        if capture_quality:
            print(
                "Capture quality: "
                f"{capture_quality.get('title', capture_quality.get('status', ''))} "
                f"({capture_quality.get('score', '-')}/100)"
            )
        print(result.message)
        if result.guidance:
            print(f"Environmental category: {result.guidance.environmental_category}")
            print(f"Guidance: {result.guidance.guidance}")
            impacts = load_environmental_impacts(config.project_root / "config" / "environmental_impacts.json")
            impact = get_environmental_impact(result.guidance.class_id, impacts)
            print(f"Bad disposal risk: {impact.risk_label}")
            print(f"Impact: {impact.bad_disposal_risks[0]}")
            print(f"Positive action: {impact.positive_action}")
        else:
            print("Suggestion: tire outra foto com o objeto centralizado, bem iluminado e com fundo menos complexo.")
        if args.save_history:
            history_path = append_history_entry(
                history_path_from_config(config),
                build_history_entry(result, source_path=args.image),
            )
            print(f"History saved: {history_path}")
    except Exception as exc:
        print(format_console_error(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
