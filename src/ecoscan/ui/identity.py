from __future__ import annotations

from typing import Any
from uuid import uuid4

from ecoscan.services.accounts import UserProfile
from ecoscan.services.identity import resolve_identity


def render_identity(st: Any) -> UserProfile:
    from streamlit.errors import StreamlitSecretNotFoundError

    try:
        auth = dict(st.secrets.get("auth", {}))
        access = dict(st.secrets.get("access", {}))
    except (StreamlitSecretNotFoundError, ValueError, TypeError):
        auth, access = {}, {}
    configured = all(auth.get(key) for key in (
        "client_id", "client_secret", "cookie_secret", "redirect_uri", "server_metadata_url",
    ))
    claims = dict(st.user) if configured else {}
    st.session_state.setdefault("visitor_identity", uuid4().hex)
    profile = resolve_identity(claims, access, st.session_state["visitor_identity"])
    previous = st.session_state.get("resolved_identity")
    if previous is not None and previous != (profile.id, profile.role):
        # Do not carry another identity's forms or analysis across a login change.
        for key in list(st.session_state):
            if key != "visitor_identity":
                del st.session_state[key]
    st.session_state["resolved_identity"] = (profile.id, profile.role)
    if claims.get("is_logged_in"):
        st.button("Sair da conta", on_click=st.logout, key="identity_logout")
        if profile.id.startswith("visitor_"):
            st.warning("Sua sessão expirou. Saia e entre novamente.")
    elif configured:
        st.button("Entrar na conta", on_click=st.login, key="identity_login")
    else:
        st.caption("Acesso público disponível. Login da secretaria ainda não configurado.")
    if st.query_params.get("profile") == "admin_secretaria" and not profile.is_admin:
        st.info("A gestão requer uma conta autorizada pela secretaria.")
    return profile
