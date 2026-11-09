from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.services.academic_report import (
    FROZEN_SOURCE_SHA,
    write_academic_report,
    write_code_appendix,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera relatório acadêmico consolidado do EcoScan.")
    parser.add_argument("--output", type=Path, default=None, help="Arquivo Markdown de saída.")
    parser.add_argument(
        "--docx", action="store_true", help="Exporta DOCX de revisão com Pandoc opcional."
    )
    parser.add_argument(
        "--code-appendix",
        action="store_true",
        help="Exporta fontes do SHA congelado; requer objeto Git local.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    try:
        output = write_academic_report(config, args.output)
        if args.code_appendix:
            write_code_appendix(config, output.parent / "apendice_codigo.zip")
        if args.docx:
            from ecoscan.services.academic_documents import write_academic_docx

            result = write_academic_docx(output, output.with_suffix(".docx"))
            write_academic_docx(
                output.parent / "ficha_aps_preenchimento_privado.md",
                output.parent / "ficha_aps_preparatoria.docx",
            )
            print(json.dumps(result, ensure_ascii=False))
        print(
            f"Base de revisão gerada; fonte {FROZEN_SOURCE_SHA}. Ficha oficial, fotos e aceite continuam pendentes."
        )
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        print(
            f"Exportação recusada ({type(exc).__name__}); confira evidências congeladas e ferramentas. Nenhum aceite foi emitido."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
