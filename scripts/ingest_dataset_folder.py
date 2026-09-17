from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config
from ecoscan.services.dataset_ingestion import DatasetIngestionError, ingest_image_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Importa imagens de uma pasta para data/raw/<classe> com validação.")
    parser.add_argument("--source-folder", type=Path, required=True, help="Pasta com imagens coletadas pelo grupo.")
    parser.add_argument("--class-id", required=True, help="Classe de destino configurada em config/settings.json.")
    parser.add_argument("--manifest", type=Path, default=None, help="Caminho opcional do manifesto CSV.")
    parser.add_argument("--recursive", action="store_true", help="Inclui subpastas da pasta de origem.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.source_folder.exists() or not args.source_folder.is_dir():
        print(f"Pasta de origem inválida: {args.source_folder}")
        return 2

    pattern = "**/*" if args.recursive else "*"
    paths = [path for path in sorted(args.source_folder.glob(pattern)) if path.is_file()]
    config = load_config()

    try:
        results = ingest_image_files(
            config,
            args.class_id,
            paths,
            manifest_path=args.manifest,
            source_note=str(args.source_folder),
        )
    except DatasetIngestionError as exc:
        print(f"Erro de configuração: {exc}")
        return 2

    saved = sum(1 for result in results if result.status == "saved")
    duplicate = sum(1 for result in results if result.status == "duplicate")
    rejected = sum(1 for result in results if result.status == "rejected")
    print(f"Importação concluída: {saved} salvas, {duplicate} duplicadas, {rejected} rejeitadas.")
    for result in results:
        print(f"{result.status}: {result.original_name} -> {result.saved_path or result.duplicate_of or result.message}")
    return 0 if rejected == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
