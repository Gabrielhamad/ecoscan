from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.services.diagnostics import dependency_status, dataset_status, model_status, write_diagnostics_report


def main() -> int:
    config = load_config()
    output = write_diagnostics_report(config, config.directories["reports"] / "diagnostics.json")
    print("EcoScan diagnostics")
    print("Dependencies:")
    for item in dependency_status():
        marker = "ok" if item.installed else "missing"
        print(f"- {item.name}: {marker} ({item.purpose})")

    dataset = dataset_status(config)
    print("Dataset totals:")
    print(f"- raw: {sum(dataset.raw_counts.values())}")
    print(f"- curated: {sum(dataset.curated_counts.values())}")
    print(f"- train: {sum(dataset.train_counts.values())}")
    print(f"- validation: {sum(dataset.validation_counts.values())}")
    print(f"- test: {sum(dataset.test_counts.values())}")

    model = model_status(config)
    print(f"Selected model: {model.selected_kind} {model.selected_path}")
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

