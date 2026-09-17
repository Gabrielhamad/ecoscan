from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.services.final_readiness import (
    build_final_readiness_items,
    format_final_readiness_markdown,
    summarize_final_readiness,
)


def main() -> int:
    config = load_config()
    items = build_final_readiness_items(config)
    output_dir = config.directories["reports"] / "final_readiness"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "estrutura_final_escalavel.md"
    output_path.write_text(format_final_readiness_markdown(items), encoding="utf-8")

    summary = summarize_final_readiness(items)
    print("Estrutura final escalável gerada.")
    print(f"Pronto: {summary.get('ready', 0)}")
    print(f"Preparado: {summary.get('prepared', 0)}")
    print(f"Depende de dados: {summary.get('needs_data', 0)}")
    print(f"Depende de treino: {summary.get('needs_training', 0)}")
    print(f"Futuro: {summary.get('future', 0)}")
    print(f"Relatório: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
