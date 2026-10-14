"""Seal or verify an existing private export; never connects to production."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ecoscan.services.backup_integrity import seal_backup, verify_backup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seal", "verify"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--revision", help="SHA Git completo; obrigatorio para seal")
    args = parser.parse_args()
    if args.action == "seal" and not args.revision:
        parser.error("seal exige --revision")
    try:
        count = (
            seal_backup(args.directory, args.revision)
            if args.action == "seal"
            else verify_backup(args.directory)
        )
    except (OSError, ValueError):
        # Do not print filenames or database contents from private export errors.
        print("Falha: confira estrutura, permissao, manifesto e integridade da copia.")
        return 1
    print(f"Integridade registrada/verificada para {count} arquivos.")
    print("Isso nao comprova completude do banco, consistencia ou restauracao.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
