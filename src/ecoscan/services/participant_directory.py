"""Restricted directory of real Auth accounts, not local demo profiles."""
from ecoscan.services.password_identity import _client, verified_profile


def registered_users(token, access):
    if not token or not verified_profile(token, access).is_admin:
        raise PermissionError("Somente analistas autenticados podem consultar cadastros.")
    rows = []
    try:
        client = _client()
        for page in range(1, 11):
            users = client.auth.admin.list_users(page=page, per_page=100)
            for user in users:
                email = str(user.email or "")
                local, _, domain = email.partition("@")
                rows.append({"identificador": "supabase_" + str(user.id),
                             "e-mail protegido": local[:1] + "***@" + domain if domain else "Não informado",
                             "confirmação": "Confirmado" if user.email_confirmed_at else "Pendente",
                             "criado em": str(user.created_at or ""),
                             "último acesso": str(user.last_sign_in_at or "Ainda não entrou")})
            if len(users) < 100:
                break
        return rows
    except Exception:
        raise OSError("Não foi possível consultar os cadastros. Tente novamente.") from None
