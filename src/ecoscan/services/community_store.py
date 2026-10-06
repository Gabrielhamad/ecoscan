"""Shared campaigns and civic reports. Service credentials stay on the server.

Every private operation revalidates Auth. UI profiles and supplied owner IDs are
never authorization. Database outages do not fall back to a local manifest.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from uuid import UUID, uuid5, NAMESPACE_URL

from PIL import Image, ImageOps

from ecoscan.services.campaigns import campaign_from_payload
from ecoscan.services.civic_reports import VALID_REVIEW_DECISIONS
from ecoscan.services.contribution_store import remote_store
from ecoscan.services.password_identity import verified_profile

REPORTS = "ecoscan_civic_reports"
CAMPAIGNS = "ecoscan_campaigns"
BUCKET = "ecoscan-civic-evidence"


def community_enabled():
    value = os.environ.get("ECOSCAN_COMMUNITY_ENABLED")
    if value is None:
        import streamlit as st
        try:
            value = st.secrets.get("community", {}).get("enabled",
                st.secrets.get("persistence", {}).get("community_enabled", False))
        except FileNotFoundError:
            value = False
    return value is True or str(value).lower() == "true"


def community_store():
    if not community_enabled():
        raise OSError("Campanhas e relatos compartilhados ainda não foram ativados. Nenhum envio será salvo apenas neste dispositivo.")
    store = remote_store()
    if store is None:
        raise OSError("Banco compartilhado sem conexão configurada.")
    return CommunityStore(store.client)


def _text(value, label, maximum, *, required=True):
    if not isinstance(value, str) or len(value.strip()) > maximum or (required and not value.strip()):
        raise ValueError(f"{label}: informe um texto de até {maximum} caracteres.")
    return value.strip()


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def private_jpeg(data: bytes) -> bytes:
    """Bounded, oriented JPEG with no EXIF/location metadata."""
    if not isinstance(data, bytes) or not data or len(data) > 15 * 1024 * 1024:
        raise ValueError("Envie uma foto JPG ou PNG de até 15 MB.")
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.format not in {"JPEG", "PNG"} or source.width * source.height > 24_000_000:
                raise ValueError()
            source.load()
            oriented = ImageOps.exif_transpose(source).convert("RGBA")
            image = Image.new("RGB", oriented.size, "white")
            image.paste(oriented, mask=oriented.getchannel("A"))
            image.thumbnail((1600, 1600))
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=82, optimize=True)
        content = output.getvalue()
        if len(content) > 1024 * 1024:
            raise ValueError()
        return content
    except (OSError, ValueError, Image.DecompressionBombError):
        raise ValueError("Foto inválida ou grande demais. Envie JPG/PNG com até 24 megapixels.") from None


class CommunityStore:
    def __init__(self, client):
        self.client = client

    def _actor(self, token, access, *, admin=False):
        if not token:
            raise PermissionError("Entre em uma conta verificada para continuar.")
        profile = verified_profile(token, access)
        if not profile.id.startswith("supabase_") or (admin and not profile.is_admin):
            raise PermissionError("Esta ação exige uma conta autorizada da secretaria.")
        return profile

    def campaign(self):
        try:
            rows = self.client.table(CAMPAIGNS).select("record,revision").eq("id", "active").execute().data
        except Exception:
            raise OSError("A campanha publicada está indisponível. Tente novamente.") from None
        if not rows:
            return None
        campaign_from_payload(rows[0]["record"])
        return rows[0]

    def publish_campaign(self, payload, *, expected_revision, token, access):
        actor = self._actor(token, access, admin=True)
        normalized = json.loads(_canonical(asdict(campaign_from_payload(payload))))
        _text(normalized["title"], "Título", 120)
        _text(normalized["public_message"], "Mensagem", 2000)
        if len(_canonical(normalized).encode()) > 60000:
            raise ValueError("Campanha muito extensa.")
        if expected_revision is not None and (type(expected_revision) is not int or expected_revision < 0):
            raise ValueError("Revisão inválida.")
        row = {"id": "active", "record": normalized, "updated_by": actor.id,
               "revision": 0 if expected_revision is None else expected_revision + 1}
        try:
            if expected_revision is None:
                result = self.client.table(CAMPAIGNS).insert(row).execute().data
            else:
                result = self.client.table(CAMPAIGNS).update(row).eq("id", "active").eq(
                    "revision", expected_revision).execute().data
        except Exception as exc:
            if getattr(exc, "code", None) == "23505":
                raise ValueError("Outra campanha já foi publicada. Atualize antes de editar.") from None
            raise OSError("Não foi possível confirmar a publicação. Atualize a campanha antes de reenviar.") from None
        if not result:
            raise ValueError("A campanha mudou durante a edição. Atualize e confira as alterações.")
        return result[0]

    def reports(self, *, token, access, own_only=False, limit=100):
        actor = self._actor(token, access)
        if type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError("Limite de consulta inválido.")
        query = self.client.table(REPORTS).select("*").order("created_at", desc=True).order("id", desc=True)
        if own_only or not actor.is_admin:
            query = query.eq("reporter_id", actor.id)
        try:
            return query.limit(limit).execute().data
        except Exception:
            raise OSError("Não foi possível consultar os relatos. O histórico não foi substituído por uma lista vazia.") from None

    def _report(self, identifier, actor):
        query = self.client.table(REPORTS).select("*").eq("id", str(UUID(identifier)))
        if not actor.is_admin:
            query = query.eq("reporter_id", actor.id)
        try:
            rows = query.execute().data
        except Exception:
            raise OSError("Protocolo indisponível. Tente novamente.") from None
        return rows[0] if rows else None

    def submit(self, record, image, *, submission_id, token, access, consent):
        actor = self._actor(token, access)
        if consent is not True:
            raise ValueError("Autorize o envio da foto e do relato para a secretaria.")
        identifier = str(uuid5(NAMESPACE_URL, actor.id + ":" + str(UUID(submission_id))))
        payload = asdict(record)
        for name, size in (("location_note", 300), ("description", 2000), ("contact", 254)):
            payload[name] = _text(payload[name], name, size, required=name != "contact")
        content = private_jpeg(image)
        digest = hashlib.sha256(content).hexdigest()
        # Only user input defines retry identity; a repeated inference can differ.
        request_hash = hashlib.sha256(_canonical({
            "image": digest, "location": payload["location_note"],
            "description": payload["description"], "contact": payload["contact"],
        }).encode()).hexdigest()
        previous = self._report(identifier, actor)
        if previous:
            return self._same_submission(previous, request_hash)
        payload.update(id=identifier, submitted_by=actor.id, evidence_path="",
                       evidence_sha256=digest, timestamp_utc=datetime.now(timezone.utc).isoformat())
        _canonical(payload)  # Reject NaN/Infinity instead of serializing invalid JSON.
        # Avoid uploading a new object when the database is already at capacity.
        # The SQL trigger remains authoritative for concurrent submissions.
        try:
            capacity = self.client.table(REPORTS).select("id").limit(200).execute().data
        except Exception:
            raise OSError("Recebimento indisponível. Nenhuma nova foto foi enviada.") from None
        if len(capacity) >= 200:
            raise ValueError("A fila do piloto está cheia. Aguarde orientação da equipe antes de enviar outra foto.")
        row = {"id": identifier, "reporter_id": actor.id, "request_hash": request_hash,
               "evidence_sha256": digest, "record": payload, "revision": 0,
               "reviews": [], "updated_by": actor.id}
        key = identifier + ".jpg"
        bucket = self.client.storage.from_(BUCKET)
        try:
            bucket.upload(key, content, file_options={"content-type": "image/jpeg", "upsert": "false"})
        except Exception:
            # A timed-out upload may have succeeded; never overwrite or delete it.
            try:
                if hashlib.sha256(bucket.download(key)).hexdigest() != digest:
                    raise ValueError()
            except Exception:
                raise OSError("Não foi possível confirmar a foto. Mantenha o formulário e tente novamente.") from None
        try:
            result = self.client.table(REPORTS).insert(row).execute().data
        except Exception:
            previous = self._report(identifier, actor)
            if previous:
                return self._same_submission(previous, request_hash)
            raise OSError("Envio ainda não confirmado. Atualize os protocolos ou reenvie o mesmo formulário; não será duplicado.") from None
        if not result:
            raise OSError("Envio sem confirmação do banco. Atualize os protocolos antes de reenviar.")
        return result[0]

    @staticmethod
    def _same_submission(row, request_hash):
        if row["request_hash"] != request_hash:
            raise ValueError("Este protocolo já existe com outros dados. Inicie um novo relato.")
        return row

    def review(self, identifier, *, expected_revision, decision, note, token, access):
        actor = self._actor(token, access, admin=True)
        if decision not in VALID_REVIEW_DECISIONS:
            raise ValueError("Decisão inválida.")
        note = _text(note, "Resposta ao participante", 2000)
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("Revisão inválida.")
        row = self._report(identifier, actor)
        if not row or row["revision"] != expected_revision:
            raise ValueError("O protocolo mudou. Atualize a fila antes de revisar.")
        if len(row["reviews"]) >= 100:
            raise ValueError("Limite de revisões atingido. Consulte o responsável pelo sistema.")
        reviews = copy.deepcopy(row["reviews"])
        reviews.append({"decision": decision, "note": note, "admin_user_id": actor.id,
                        "timestamp_utc": datetime.now(timezone.utc).isoformat()})
        try:
            result = self.client.table(REPORTS).update({"reviews": reviews,
                "revision": expected_revision + 1, "updated_by": actor.id}).eq(
                    "id", row["id"]).eq("revision", expected_revision).execute().data
        except Exception:
            raise OSError("Não foi possível confirmar a decisão. Atualize a fila antes de repetir.") from None
        if not result:
            raise ValueError("Outro analista revisou este protocolo. Atualize a fila.")
        return result[0]

    def evidence(self, identifier, *, token, access):
        actor = self._actor(token, access)
        row = self._report(identifier, actor)
        if not row:
            raise PermissionError("Protocolo não encontrado ou não autorizado.")
        try:
            content = self.client.storage.from_(BUCKET).download(row["id"] + ".jpg")
            if hashlib.sha256(content).hexdigest() != row["evidence_sha256"]:
                raise ValueError()
            return content
        except Exception:
            raise OSError("Não foi possível carregar uma evidência íntegra. Tente novamente.") from None
