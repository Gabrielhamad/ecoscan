"""Export the same before/after evidence shown in the application."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ecoscan.app.pipeline import run_processing_pipeline
from ecoscan.config import load_config
from ecoscan.services.visual_report import save_pipeline_artifacts


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export actual processing with the configured defaults.")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run_processing_pipeline(args.image, load_config())
    artifacts = save_pipeline_artifacts(result, args.output)
    reproduction = {
        "input_file_sha256": hashlib.sha256(args.image.read_bytes()).hexdigest(),
        "settings_file_sha256": hashlib.sha256((PROJECT_ROOT / "config/settings.json").read_bytes()).hexdigest(),
        "filter": result.filter_result.name,
        "segmentation": result.segmentation_result.name,
        "morphology": result.morphology_result.metadata,
        "scope": "Processamento real; este comando não calcula uma previsão nem a acurácia.",
    }
    (args.output / "reproduction.json").write_text(
        json.dumps(reproduction, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Evidence exported: {len(artifacts)} artifacts in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
