from __future__ import annotations

from typing import Any
from uuid import uuid4
import time

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
    if not configured:
        from ecoscan.services.contribution_store import persistent_enabled
        try:
            if persistent_enabled():
                return _render_password_identity(st, access)
        except (ValueError, OSError):
            st.warning("Login temporariamente indisponível. Você pode continuar como visitante.")
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


def _render_password_identity(st, access):
    from ecoscan.services.password_identity import sign_in, verified_profile

    st.session_state.setdefault("visitor_identity", uuid4().hex)
    profile = resolve_identity({}, {}, st.session_state["visitor_identity"])
    token = st.session_state.get("auth_access_token")
    if token:
        try:
            profile = verified_profile(token, access)
        except ValueError as exc:
            st.session_state.pop("auth_access_token", None)
            st.warning(str(exc))
    current = (profile.id, profile.role)
    if st.session_state.get("resolved_identity") not in (None, current):
        for key in list(st.session_state):
            if key not in ("visitor_identity", "auth_access_token"):
                del st.session_state[key]
    st.session_state["resolved_identity"] = current
    if profile.id.startswith("supabase_"):
        st.caption("Conectado como " + ("analista da secretaria" if profile.is_admin else "cidadão"))
        if st.button("Sair da conta", key="password_logout"):
            # Tokens are session-only. No persistent browser cookie is created.
            st.session_state.clear()
            st.rerun()
    else:
        with st.expander("Entrar ou criar conta"):
            st.caption("Visitante: análise temporária, mapa e orientações. Conta verificada: contribuições e participação vinculadas ao seu perfil.")
            login_tab, signup_tab = st.tabs(["Entrar", "Criar conta"])
            with signup_tab:
                _render_registration(st, access)
                if access.get("public_signup_enabled") is True:
                    _render_resend_confirmation(st)
            with login_tab:
                _render_login_form(st)
    if st.query_params.get("profile") == "admin_secretaria" and not profile.is_admin:
        st.info("A gestão requer uma conta autorizada pela secretaria.")
    return profile


def _render_registration(st, access):
    from ecoscan.services.password_identity import register
    enabled = access.get("public_signup_enabled") is True
    if not enabled:
        st.info("Cadastro em preparação. O modo visitante continua disponível, sem salvar fotos, relatos ou pontos no perfil.")
        return
    with st.form("account_registration", clear_on_submit=True):
        email = st.text_input("E-mail", max_chars=254, key="signup_email")
        password = st.text_input("Senha (mínimo 12 caracteres)", type="password", max_chars=128)
        confirmation = st.text_input("Confirmar senha", type="password", max_chars=128)
        st.caption("E-mail e credenciais são tratados pelo Supabase Auth para acesso à conta. Fotos só são guardadas quando você autoriza uma contribuição.")
        consent = st.checkbox("Concordo com o uso do meu e-mail para criar e verificar minha conta.")
        submit = st.form_submit_button("Solicitar cadastro")
    if submit:
        if not consent:
            st.error("Confirme o uso do e-mail antes de continuar.")
            return
        now = time.monotonic()
        if now - st.session_state.get("signup_last_attempt", -60) < 60:
            st.warning("Aguarde um minuto antes de tentar novamente.")
            return
        st.session_state["signup_last_attempt"] = now
        try:
            register(email, password, confirmation, enabled=enabled)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.success("Solicitação recebida. Se o cadastro puder prosseguir, você receberá um e-mail de confirmação. Verifique também o spam. Depois de confirmar, volte para Entrar.")


def _render_login_form(st):
    from ecoscan.services.password_identity import sign_in
    with st.form("password_login", clear_on_submit=True):
        email = st.text_input("E-mail", max_chars=254)
        password = st.text_input("Senha", type="password", max_chars=256)
        submit = st.form_submit_button("Entrar")
    if submit:
        try:
            st.session_state["auth_access_token"] = sign_in(email, password)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.rerun()
    st.caption("Esqueceu a senha? Solicite recuperação ao responsável do grupo. Nunca envie sua senha por mensagem.")


def _render_resend_confirmation(st):
    from ecoscan.services.password_identity import resend_confirmation
    with st.expander("Não recebi a confirmação"):
        with st.form("resend_confirmation", clear_on_submit=True):
            email = st.text_input("E-mail do cadastro", max_chars=254)
            sent = st.form_submit_button("Reenviar confirmação")
        if sent:
            now = time.monotonic()
            if now - st.session_state.get("signup_last_attempt", -60) < 60:
                st.warning("Aguarde um minuto antes de solicitar outro e-mail.")
                return
            st.session_state["signup_last_attempt"] = now
            try:
                resend_confirmation(email, enabled=True)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Se houver um cadastro pendente para esse e-mail, a confirmação será reenviada. Confira também o spam.")
