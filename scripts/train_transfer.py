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
from ecoscan.errors import format_console_error
from ecoscan.training.transfer_learning import build_training_plan, save_training_plan, train_tensorflow_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare or run EcoScan transfer learning training.")
    parser.add_argument("--run", action="store_true", help="Actually train the TensorFlow model. Without this, only a plan is written.")
    parser.add_argument("--plan-output", type=Path, default=PROJECT_ROOT / "reports" / "training" / "training_plan.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config()
        plan = build_training_plan(config)
        plan_path = save_training_plan(plan, args.plan_output)
    except Exception as exc:
        print(format_console_error(exc))
        return 1

    print(f"Training plan written: {plan_path}")

    if not args.run:
        print("Dry run only. Use --run after cleaning the dataset and installing TensorFlow/Python 3.12.")
        return 0

    try:
        result = train_tensorflow_model(config, plan=plan)
    except Exception as exc:
        print(format_console_error(exc))
        return 1

    print("EcoScan transfer learning training complete.")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
