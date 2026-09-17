from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.services.dataset_governance import build_dataset_readiness, write_dataset_readiness_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera relatório de prontidão do dataset EcoScan.")
    parser.add_argument("--target-per-class", type=int, default=50, help="Alvo mínimo de imagens curadas por classe.")
    parser.add_argument("--output", type=Path, default=None, help="Pasta de saída. Padrão: reports/dataset_readiness.")
    parser.add_argument("--strict", action="store_true", help="Retorna código 1 se o dataset ainda não estiver pronto.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    summary, rows = build_dataset_readiness(config, target_per_class=args.target_per_class)
    written = write_dataset_readiness_report(
        config,
        target_per_class=args.target_per_class,
        output_dir=args.output,
    )

    print("EcoScan dataset readiness")
    print(f"Target per class: {summary.target_per_class}")
    print(f"Raw target: {summary.classes_at_raw_target}/{summary.class_count}")
    print(f"Curated target: {summary.classes_at_curated_target}/{summary.class_count}")
    print(f"Missing raw images: {summary.missing_raw_total}")
    print(f"Ready for final training: {summary.ready_for_final_training}")
    for row in rows:
        print(f"- {row.class_id}: {row.gate} ({row.next_action})")
    print(f"CSV: {written['csv']}")
    print(f"JSON: {written['json']}")
    print(f"Markdown: {written['markdown']}")
    return 0 if summary.ready_for_final_training or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
