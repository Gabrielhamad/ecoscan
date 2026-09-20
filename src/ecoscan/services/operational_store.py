"""Server-only operational persistence; failures never fall back to local files."""
from __future__ import annotations

import os

from ecoscan.services.contribution_store import remote_store


TABLES = {"points": "ecoscan_points", "field_tests": "ecoscan_field_tests"}


def operations_enabled():
    value = os.environ.get("ECOSCAN_OPERATIONS_ENABLED")
    if value is None:
        import streamlit as st
        try:
            value = st.secrets.get("persistence", {}).get("operations_enabled", False)
        except FileNotFoundError:
            value = False
    return value is True or str(value).lower() == "true"


def operational_store():
    # Explicit rollout gate, not a fallback after a failed database request.
    if not operations_enabled():
        return None
    remote = remote_store()
    if remote is None:
        raise OSError("Banco operacional ativado sem credenciais. Configure a conexão antes de continuar.")
    return OperationalStore(remote.client)


class OperationalStore:
    def __init__(self, client):
        self.client = client

    def append(self, kind, payload):
        table = TABLES[kind]
        if kind == "points":
            if payload["user_id"].startswith("visitor_"):
                raise ValueError("Entre em uma conta para acumular pontos permanentes.")
            row = {"id": payload["id"], "user_id": payload["user_id"],
                   "mission_id": payload["mission_id"], "evidence_sha256": payload["evidence_sha256"],
                   "record": payload}
        else:
            row = {"id": payload["id"], "tester_id": payload["tester_id"], "record": payload}
        try:
            self.client.table(table).insert(row).execute()
        except Exception as exc:
            if getattr(exc, "code", None) == "23505":
                raise ValueError("Este registro já foi recebido. Atualize antes de tentar novamente.") from None
            raise OSError("Não foi possível confirmar a gravação no banco. Confira seu histórico antes de reenviar.") from None

    def read(self, kind, *, owner=None, limit=None):
        table = TABLES[kind]
        owner_field = "user_id" if kind == "points" else "tester_id"
        if limit is not None and limit <= 0:
            return []
        rows, offset = [], 0
        try:
            # Stable order and pagination avoid Supabase's default 1000-row truncation.
            while True:
                size = min(500, limit - len(rows)) if limit is not None else 500
                query = self.client.table(table).select("record").order("created_at", desc=True).order("id", desc=True)
                if owner is not None:
                    query = query.eq(owner_field, owner)
                batch = query.range(offset, offset + size - 1).execute().data
                rows.extend(item["record"] for item in batch)
                if len(batch) < size or (limit is not None and len(rows) >= limit):
                    break
                offset += size
        except Exception:
            raise OSError("Histórico indisponível no banco. Não foi substituído por um histórico vazio ou temporário.") from None
        return list(reversed(rows))
