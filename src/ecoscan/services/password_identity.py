"""Supabase Auth verification; credentials and clients never enter shared caches."""
from __future__ import annotations

from uuid import UUID
import re

from ecoscan.services.accounts import UserProfile
from ecoscan.services.contribution_store import settings


def _client():
    from supabase import create_client
    url, key = settings()
    if not url or not key:
        raise ValueError("Login indisponível.")
    return create_client(url, key)


def sign_in(email: str, password: str) -> str:
    if not email.strip() or not password:
        raise ValueError("Preencha e-mail e senha.")
    try:
        result = _client().auth.sign_in_with_password({"email": email.strip(), "password": password})
        if not result.session or not result.session.access_token:
            raise ValueError()
        return result.session.access_token
    except Exception:
        raise ValueError("Não foi possível entrar. Confira seus dados e a confirmação da conta, ou tente novamente mais tarde.") from None


def register(email: str, password: str, confirmation: str, *, enabled: bool = False) -> None:
    if enabled is not True:
        raise ValueError("Cadastro ainda em preparação. Você pode continuar como visitante.")
    email = email.strip()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Informe um e-mail válido.")
    if not 12 <= len(password) <= 128:
        raise ValueError("Use uma senha com 12 a 128 caracteres.")
    if password != confirmation:
        raise ValueError("As senhas não coincidem.")
    try:
        # Standard signup, never admin.create_user or an email-confirmation bypass.
        _client().auth.sign_up({"email": email, "password": password})
    except Exception:
        raise ValueError("Não foi possível solicitar o cadastro. Aguarde e tente novamente. Se persistir, avise o responsável pelo EcoScan.") from None


def resend_confirmation(email: str, *, enabled: bool = False) -> None:
    if enabled is not True:
        raise ValueError("Confirmação por e-mail ainda em preparação.")
    email = email.strip()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Informe um e-mail válido.")
    try:
        _client().auth.resend({"type": "signup", "email": email})
    except Exception:
        raise ValueError("Não foi possível solicitar o reenvio. Aguarde e tente novamente; se persistir, avise o responsável pelo EcoScan.") from None


def verified_profile(token: str, access: dict) -> UserProfile:
    try:
        # Always verify with Auth, not untrusted JWT decoding or user metadata.
        user = _client().auth.get_user(token).user
        identifier = str(UUID(str(user.id)))
        if not user.email or not user.email_confirmed_at:
            raise ValueError()
        allowed = access.get("supabase_admin_emails", [])
        if not isinstance(allowed, (list, tuple)):
            allowed = []
        is_admin = user.email.strip().casefold() in {
            str(email).strip().casefold() for email in allowed}
        return UserProfile(
            id="supabase_" + identifier, display_name="Analista" if is_admin else "Participante",
            role="admin" if is_admin else "user",
            organization="Secretaria do Meio Ambiente" if is_admin else "Comunidade",
            notes="Conta autenticada. Os protocolos enviados com esta conta ficam vinculados a ela.",
        )
    except Exception:
        raise ValueError("Sua sessão não pôde ser validada. Entre novamente.") from None
