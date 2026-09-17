from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping
from typing import Any

from ecoscan.services.accounts import UserProfile


def resolve_identity(
    claims: Mapping[str, Any],
    access: Mapping[str, Any],
    visitor_id: str,
    *,
    now: float | None = None,
) -> UserProfile:
    """Consume only claims verified by Streamlit's OIDC provider, never URL data."""
    issuer = claims.get("iss")
    subject = claims.get("sub")
    try:
        expires = float(claims.get("exp", 0))
    except (TypeError, ValueError):
        expires = 0
    valid = (
        claims.get("is_logged_in") is True
        and isinstance(issuer, str) and bool(issuer)
        and isinstance(subject, str) and bool(subject)
        and expires > (time.time() if now is None else now)
    )
    if not valid:
        return UserProfile(
            id=f"visitor_{visitor_id}", display_name="Visitante", role="user",
            organization="Comunidade",
            notes="Histórico temporário desta sessão. Entre para manter sua identificação.",
        )
    identity_key = json.dumps([issuer, subject], ensure_ascii=True).encode()
    user_id = "oidc_" + hashlib.sha256(identity_key).hexdigest()
    allowed = access.get("admin_emails", [])
    if not isinstance(allowed, (list, tuple)):
        allowed = []
    email = str(claims.get("email", "")).strip().casefold()
    is_admin = (
        issuer == access.get("issuer")
        and claims.get("email_verified") is True
        and bool(email)
        and email in {str(value).strip().casefold() for value in allowed}
    )
    return UserProfile(
        id=user_id, display_name=str(claims.get("name") or "Usuário EcoScan"),
        role="admin" if is_admin else "user",
        organization="Secretaria do Meio Ambiente" if is_admin else "Comunidade",
        notes="Conta autenticada.",
    )
