from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.errors import format_console_error
from ecoscan.services.acceptance_checks import run_acceptance_checks
from ecoscan.utils.logging_config import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run EcoScan acceptance checks for APS delivery.")
    parser.add_argument("--sample-image", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config()
        configure_logging(config.directories["logs"], include_stream=False)
        report = run_acceptance_checks(
            config,
            output_dir=args.output,
            sample_image=args.sample_image,
        )
    except Exception as exc:
        print(format_console_error(exc))
        return 1

    summary = report.summary
    print("Validação de aceite concluída.")
    print(f"OK: {summary.get('ok', 0)}")
    print(f"Atenção: {summary.get('attention', 0)}")
    print(f"Pendente: {summary.get('pending', 0)}")
    print(f"Falha: {summary.get('failed', 0)}")
    output_dir = args.output or config.directories["reports"] / "acceptance_checks"
    print(f"Relatório: {Path(output_dir).resolve() / 'acceptance_checks.md'}")
    return 1 if summary.get("failed", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
