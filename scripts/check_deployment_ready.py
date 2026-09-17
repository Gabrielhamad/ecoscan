from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.services.deployment_readiness import build_free_hosting_plan, format_free_hosting_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check EcoScan free hosting readiness.")
    parser.add_argument(
        "--output",
        default="reports/deployment_readiness/hospedagem_gratuita.md",
        help="Markdown report path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    plan = build_free_hosting_plan(config)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(format_free_hosting_markdown(plan), encoding="utf-8")
    attention = sum(1 for check in plan.checks if check.status != "ok")
    print(f"Relatorio de hospedagem gerado em {output_path}")
    print(f"Itens em atencao: {attention}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
