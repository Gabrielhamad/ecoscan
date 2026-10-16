"""Supabase Auth verification; credentials and clients never enter shared caches."""
from __future__ import annotations

from uuid import UUID, uuid4
import logging
import re

from ecoscan.services.accounts import UserProfile
from ecoscan.services.contribution_store import settings


logger = logging.getLogger(__name__)


def _auth_failure(exc: Exception, operation: str) -> ValueError:
    # Only allowlisted codes enter logs; provider messages may contain credentials.
    messages = {
        "over_email_send_rate_limit": "O limite temporário de e-mails foi atingido. Aguarde antes de solicitar outro envio.",
        "over_request_rate_limit": "Muitas tentativas em pouco tempo. Aguarde antes de tentar novamente.",
        "email_not_confirmed": "Confirme seu e-mail antes de entrar. Use 'Não recebi a confirmação' para solicitar outro envio.",
        "invalid_credentials": "Não foi possível entrar. Confira e-mail e senha ou solicite a recuperação de senha.",
        "weak_password": "A senha não atende aos critérios de segurança. Escolha outra senha com pelo menos 12 caracteres.",
        "signup_disabled": "O cadastro está temporariamente desabilitado. Avise o responsável pelo EcoScan.",
        "email_address_not_authorized": "O serviço de e-mail ainda não permite este envio. Avise o responsável pelo EcoScan.",
        "captcha_failed": "A verificação de segurança não foi concluída. Avise o responsável pelo EcoScan.",
        "email_address_invalid": "O serviço não aceitou este endereço de e-mail. Confira o endereço informado.",
    }
    raw_code = getattr(exc, "code", None)
    code = raw_code if isinstance(raw_code, str) and raw_code in messages else "provider_unavailable"
    if getattr(exc, "status", None) in (429, "429"):
        code = "over_request_rate_limit" if code == "provider_unavailable" else code
    reference = uuid4().hex[:12]
    logger.warning("auth_failure operation=%s code=%s reference=%s", operation, code, reference)
    message = messages.get(code, "O serviço de acesso não concluiu a solicitação. Tente novamente mais tarde; se persistir, informe este código ao suporte.")
    return ValueError(f"{message} Código de atendimento: {reference}.")


def validate_email(email: str) -> str:
    email = email.strip()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Informe um e-mail válido.")
    return email


def validate_registration(email: str, password: str, confirmation: str) -> str:
    email = validate_email(email)
    if not 12 <= len(password) <= 128:
        raise ValueError("Use uma senha com 12 a 128 caracteres.")
    if password != confirmation:
        raise ValueError("As senhas não coincidem.")
    return email


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
    except Exception as exc:
        raise _auth_failure(exc, "login") from None


def register(email: str, password: str, confirmation: str, *, enabled: bool = False) -> None:
    if enabled is not True:
        raise ValueError("Cadastro ainda em preparação. Você pode continuar como visitante.")
    email = validate_registration(email, password, confirmation)
    try:
        # Standard signup, never admin.create_user or an email-confirmation bypass.
        _client().auth.sign_up({"email": email, "password": password})
    except Exception as exc:
        raise _auth_failure(exc, "signup") from None


def resend_confirmation(email: str, *, enabled: bool = False) -> None:
    if enabled is not True:
        raise ValueError("Confirmação por e-mail ainda em preparação.")
    email = validate_email(email)
    try:
        _client().auth.resend({"type": "signup", "email": email})
    except Exception as exc:
        raise _auth_failure(exc, "resend") from None


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
    email = validate_email(email)
    try:
        # The recovery template uses SiteURL and TokenHash; no caller-controlled redirect.
        _client().auth.reset_password_for_email(email)
    except Exception as exc:
        raise _auth_failure(exc, "recovery_request") from None


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
