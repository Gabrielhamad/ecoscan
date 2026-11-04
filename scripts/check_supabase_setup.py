"""Diagnose the configured Supabase project without printing or changing data."""
from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.services.contribution_store import remote_store, settings
from ecoscan.services.supabase_readiness import inspect_supabase


def main() -> int:
    try:
        url, key = settings()
    except ValueError as exc:
        print(f"Configuração: FALHA — {exc}")
        return 2
    if not url or not key:
        print("Configuração: PENDENTE — Supabase não configurado neste ambiente.")
        return 2

    print("Configuração: OK — URL e chave privada presentes (valores ocultos).")
    try:
        store = remote_store()
        checks = inspect_supabase(store.client)
    except OSError as exc:
        print(f"Conexão: FALHA — {exc}")
        return 1

    for check in checks:
        status = "OK" if check.ok else "FALHA"
        print(f"{status}: {check.item} — {check.detail}")
    failures = sum(not check.ok for check in checks)
    print(f"Resultado: {len(checks) - failures} OK; {failures} falha(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
