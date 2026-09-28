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


def request_password_reset(email: str) -> None:
    """Send the provider's recovery email without disclosing account existence."""
    email = email.strip()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Informe um e-mail válido.")
    try:
        # The recovery template uses SiteURL and TokenHash; no caller-controlled redirect.
        _client().auth.reset_password_for_email(email)
    except Exception:
        raise ValueError("Não foi possível solicitar a recuperação. Aguarde e tente novamente.") from None


def reset_password(token_hash: str, password: str, confirmation: str) -> None:
    """Consume a recovery link only on explicit submission, using an isolated client.

    Never use the current login, a supplied user ID, or the admin password API.
    The recovery session stays in this call and is not promoted to an app login.
    """
    if not 12 <= len(password) <= 128:
        raise ValueError("Use uma senha com 12 a 128 caracteres.")
    if password != confirmation:
        raise ValueError("As senhas não coincidem.")
    if not isinstance(token_hash, str) or not re.fullmatch(r"[a-fA-F0-9]{32,128}", token_hash):
        raise ValueError("Link inválido. Solicite uma nova recuperação.")
    client = None
    authenticated = False
    try:
        client = _client()
        result = client.auth.verify_otp({"token_hash": token_hash, "type": "recovery"})
        if not result.session or not result.session.access_token:
            raise ValueError()
        authenticated = True
        if not result.user or not result.user.email_confirmed_at:
            raise ValueError()
        # verify_otp installs this recovery session on this fresh Auth client.
        updated = client.auth.update_user({"password": password})
        if not updated.user or updated.user.id != result.user.id:
            raise ValueError()
    except Exception:
        raise ValueError("Não foi possível redefinir a senha. O link pode ter expirado ou já ter sido usado. Solicite uma nova recuperação e tente novamente.") from None
    finally:
        if authenticated:
            try:
                client.auth.sign_out({"scope": "local"})
            except Exception:
                # A logout outage must not turn a confirmed password update into failure.
                pass
