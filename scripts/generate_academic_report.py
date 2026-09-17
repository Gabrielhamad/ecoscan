from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.services.academic_report import write_academic_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera relatório acadêmico consolidado do EcoScan.")
    parser.add_argument("--output", type=Path, default=None, help="Arquivo Markdown de saída.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    output = write_academic_report(config, args.output)
    print(f"Relatório acadêmico gerado: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
