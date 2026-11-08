"""Create an auditable execution candidate; no release/tag bypass is provided."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ecoscan.config import load_config
from ecoscan.services.delivery_pack import write_delivery_pack, write_execution_archive
from ecoscan.services.execution_package import verify_execution_archive


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    review = commands.add_parser("review")
    review.add_argument("--ref", required=True, help="Committed source ref; full SHA recorded")
    review.add_argument(
        "--runtime-lock", type=Path, required=True, help="Reviewed exact/hash runtime lock"
    )
    review.add_argument(
        "--lock-ref", help="Optional Git provenance of requirements.lock, verified byte for byte"
    )
    review.add_argument(
        "--ci-report", type=Path, help="Sanitized CI observation for the source SHA"
    )
    review.add_argument("--output", type=Path, required=True, help="New ignored reports/ directory")
    review.add_argument("--photos-root", type=Path)
    review.add_argument("--photos-manifest", type=Path)
    inspect = commands.add_parser("verify")
    inspect.add_argument("archive", type=Path)
    legacy = commands.add_parser(
        "legacy-report", help="Local inventory only; not an executable package or release approval"
    )
    legacy.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "verify":
            print(json.dumps(verify_execution_archive(args.archive), ensure_ascii=False))
        elif args.action == "legacy-report":
            write_delivery_pack(load_config(), args.output)
            print("Inventario local gerado; nao aprova release nem substitui o pacote executavel.")
        else:
            paths = write_execution_archive(
                load_config(),
                args.output,
                ref=args.ref,
                runtime_lock=args.runtime_lock,
                builder_root=PROJECT_ROOT,
                lock_ref=args.lock_ref,
                ci_report=args.ci_report,
                photos_root=args.photos_root,
                photos_manifest=args.photos_manifest,
            )
            verified = verify_execution_archive(paths["archive"])
            print(json.dumps(verified, ensure_ascii=False))
            print(
                "Candidato de revisao gerado. Release/tag bloqueadas ate CI e aceite do SHA; nenhuma publicacao foi executada."
            )
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
        zipfile.BadZipFile,
    ) as exc:
        print(
            f"Pacote recusado ({type(exc).__name__}). Confira snapshot, lock, licencas e hashes; nenhum segredo sera exibido."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
