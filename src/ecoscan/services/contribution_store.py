"""Private server-side Supabase persistence for the pilot's reviewed photos."""
from __future__ import annotations

import copy
import os
from uuid import UUID


def settings():
    url = os.environ.get("ECOSCAN_SUPABASE_URL", "")
    key = os.environ.get("ECOSCAN_SUPABASE_SERVICE_KEY", "")
    if not url and not key:
        import streamlit as st
        try:
            section = st.secrets.get("persistence", {})
        except FileNotFoundError:
            section = {}
        url, key = section.get("url", ""), section.get("service_key", "")
    if bool(url) != bool(key):
        raise ValueError("Configuração do banco incompleta. Informe URL e chave privada em Secrets.")
    if url and (not url.startswith("https://") or not url.endswith(".supabase.co")):
        raise ValueError("Use a URL HTTPS do projeto Supabase, sem barra final.")
    return url, key


def persistent_enabled():
    return bool(settings()[0])


def remote_store():
    url, key = settings()
    if not url:
        return None
    try:
        from supabase import create_client
        return SupabaseContributions(create_client(url, key))
    except Exception:
        raise OSError("Não foi possível conectar ao banco. Nenhum fallback temporário foi ativado.") from None


class SupabaseContributions:
    def __init__(self, client):
        self.client = client

    def list(self):
        try:
            rows = self.client.table("ecoscan_contributions").select("record").order("created_at", desc=True).limit(200).execute().data
            return [row["record"] for row in rows]
        except Exception:
            raise OSError("Banco indisponível. Tente novamente; os relatos não serão salvos apenas nesta sessão.") from None

    def save(self, record, *, image=None, previous_revision=None):
        data = copy.deepcopy(record)
        identifier = str(UUID(data["id"]))
        # Remote records never contain machine-specific paths.
        data["feedback"].pop("image_path", None)
        data["storage_key"] = f"{identifier}.jpg"
        row = {"id": identifier, "reporter_id": data["reporter_id"],
               "image_sha256": data["image_sha256"], "revision": data.get("revision", 0),
               "record": data}
        try:
            if image is not None:
                if len(image) > 1024 * 1024:
                    raise ValueError("A foto da contribuição excede 1 MB após compressão.")
                self.client.storage.from_("ecoscan-contributions").upload(
                    data["storage_key"], image,
                    file_options={"content-type": "image/jpeg", "upsert": "false"})
                self.client.table("ecoscan_contributions").insert(row).execute()
            else:
                if previous_revision is None:
                    raise ValueError("Revisão anterior obrigatória.")
                updated = self.client.table("ecoscan_contributions").update(row).eq(
                    "id", identifier).eq("revision", previous_revision).execute().data
                if not updated:
                    raise ValueError("O protocolo mudou. Atualize a fila antes de revisar.")
        except ValueError:
            raise
        except Exception:
            # Do not delete on an ambiguous timeout: the insert may have committed.
            raise OSError("Não foi possível confirmar a gravação. Atualize os protocolos antes de reenviar.") from None
        return data

    def image(self, record):
        key = f"{UUID(record['id'])}.jpg"
        try:
            return self.client.storage.from_("ecoscan-contributions").download(key)
        except Exception:
            raise OSError("Foto indisponível no armazenamento privado. Tente novamente.") from None
