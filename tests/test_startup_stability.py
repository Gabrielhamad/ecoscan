from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from ecoscan.services.accounts import UserProfile
from ecoscan.services.password_identity import AuthenticationUnavailableError, verified_profile
from ecoscan.services.supabase_client import create_bounded_client

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("role", ["user", "admin"])
def test_entry_does_not_query_hidden_pages_and_navigation_is_lazy(role):
    profile = UserProfile("supabase_test", "Participante", role)
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=20)
    with ExitStack() as stack:
        stack.enter_context(patch("ecoscan.ui.streamlit_app.render_identity", return_value=profile))
        functions = ("_load_campaign_config", "_render_account_tab", "_render_admin_tab",
                     "_render_campaign_tab", "_render_civic_reports_tab", "_render_overview_strip",
                     "_render_acceptance_checks", "_render_collection_points_tab")
        calls = {name: stack.enter_context(patch("ecoscan.ui.streamlit_app." + name)) for name in functions}
        app.run()
        assert not app.exception
        for call in calls.values():
            call.assert_not_called()
        # Photo capture widgets stay mounted across navigation; their input is
        # not discarded by lazy mounting of the account or administration tabs.
        uploads_before = len(app.get("file_uploader")) + len(app.get("camera_input"))
        app.session_state["main_navigation_" + role] = "Conta" if role == "admin" else "Perfil"
        app.run()
        assert not app.exception
        calls["_render_account_tab"].assert_called_once()
        calls["_load_campaign_config"].assert_called_once()
        calls["_render_admin_tab"].assert_not_called()
        assert len(app.get("file_uploader")) + len(app.get("camera_input")) == uploads_before
        app.session_state["main_navigation_" + role] = "Análise" if role == "admin" else "Escanear"
        app.run()
        assert not app.exception
        calls["_load_campaign_config"].assert_called_once()
        calls["_render_account_tab"].assert_called_once()


def password_app():
    app = AppTest.from_string('''
import streamlit as st
from ecoscan.ui.identity import _render_password_identity
profile = _render_password_identity(st, {})
st.write("PRIVATE_CONTENT:" + profile.id)
''')
    app.session_state["auth_access_token"] = "private-token"
    app.session_state["resolved_identity"] = ("supabase_test", "user")
    app.session_state["unsent_draft"] = "keep across temporary outage"
    return app


def test_closed_directory_does_not_paginate_auth_accounts():
    app = AppTest.from_string('''
import streamlit as st
from ecoscan.config import load_config
from ecoscan.services.accounts import UserProfile
from ecoscan.ui.streamlit_app import _render_admin_tab
_render_admin_tab(st, load_config(), UserProfile("supabase_admin", "Admin", "admin"), (), None, [], {})
''')
    app.secrets["access"] = {}
    with ExitStack() as stack:
        stack.enter_context(patch("ecoscan.ui.learning.render_review"))
        for name in ("_render_admin_campaign_operations", "_render_admin_recognition_quality",
                     "_render_admin_field_tests"):
            stack.enter_context(patch("ecoscan.ui.admin_views." + name))
        stack.enter_context(patch("ecoscan.ui.community.render_campaign_editor"))
        stack.enter_context(patch("ecoscan.ui.community.render_reports"))
        stack.enter_context(patch("ecoscan.ui.admin_views.read_point_transactions", return_value=[]))
        stack.enter_context(patch("ecoscan.ui.admin_views.summarize_points_by_user", return_value=[]))
        directory = stack.enter_context(patch("ecoscan.services.participant_directory.registered_users", return_value=[]))
        app.run()
        assert not app.exception
        directory.assert_not_called()
        app.session_state["real_users_panel"] = True
        app.run()
        assert not app.exception
        directory.assert_called_once()


def test_temporary_outage_keeps_session_blocks_content_and_retry_recovers():
    app = password_app()
    with patch("ecoscan.services.password_identity.verified_profile",
               side_effect=AuthenticationUnavailableError("Tente novamente")) as verify:
        app.run()
        assert not app.exception
        assert app.session_state["auth_access_token"] == "private-token"
        assert app.session_state["unsent_draft"] == "keep across temporary outage"
        assert not any("PRIVATE_CONTENT:" in item.value for item in app.markdown)
        next(b for b in app.button if b.key == "retry_identity").click().run()
        assert verify.call_count == 2  # One call per run, no immediate retry loop.
    with patch("ecoscan.services.password_identity.verified_profile",
               return_value=UserProfile("supabase_test", "Participante", "user")):
        next(b for b in app.button if b.key == "retry_identity").click().run()
        assert not app.exception
        assert any("PRIVATE_CONTENT:supabase_test" in item.value for item in app.markdown)
        assert app.session_state["unsent_draft"] == "keep across temporary outage"


def test_invalid_session_clears_token_and_previous_identity_data():
    app = password_app()
    with patch("ecoscan.services.password_identity.verified_profile", side_effect=ValueError("Sessão inválida")):
        app.run()
    assert not app.exception
    assert "auth_access_token" not in app.session_state
    assert "unsent_draft" not in app.session_state
    assert not any("PRIVATE_CONTENT:supabase_test" in item.value for item in app.markdown)


def test_guest_option_after_outage_discards_private_session():
    app = password_app()
    with patch("ecoscan.services.password_identity.verified_profile",
               side_effect=AuthenticationUnavailableError("Indisponível")):
        app.run()
        next(b for b in app.button if b.key == "identity_continue_visitor").click().run()
    assert not app.exception
    assert "auth_access_token" not in app.session_state
    assert "unsent_draft" not in app.session_state
    assert app.session_state["resolved_identity"][0].startswith("visitor_")


@pytest.mark.parametrize("failure", [httpx.ReadTimeout("PRIVATE_TOKEN"), httpx.ConnectError("PRIVATE_TOKEN")])
def test_transport_failure_is_temporary_redacted_and_closes_client(failure):
    client = MagicMock()
    client.auth.get_user.side_effect = failure
    with patch("ecoscan.services.password_identity._client", return_value=client):
        with pytest.raises(AuthenticationUnavailableError) as error:
            verified_profile("token", {})
    assert "PRIVATE_TOKEN" not in str(error.value)
    client.auth.close.assert_called_once()


def test_real_sdk_propagates_timeout_policy_and_isolates_clients(monkeypatch):
    # Import subclasses of httpx.Client before replacing its factory below.
    import supabase
    assert callable(supabase.create_client)
    original = httpx.Client
    requests, clients = [], []

    def handle(request):
        requests.append(request)
        if request.url.path.endswith("/user"):
            return httpx.Response(200, json={"id": "e6d28f19-2ef6-4eb2-a35a-67de3c4c0f14",
                "aud": "authenticated", "app_metadata": {}, "user_metadata": {},
                "created_at": "2026-01-01T00:00:00Z", "email": "person@example.com",
                "email_confirmed_at": "2026-01-01T00:00:00Z"})
        return httpx.Response(200, json=[])

    def transport(**kwargs):
        client = original(transport=httpx.MockTransport(handle), **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(httpx, "Client", transport)
    first = create_bounded_client("https://example.supabase.co", "test-key")
    second = create_bounded_client("https://example.supabase.co", "test-key")
    try:
        first.auth.get_user("token-a")
        second.auth.get_user("token-b")
        first.table("ecoscan_campaigns").select("record").execute()
        assert requests[0].headers["authorization"] == "Bearer token-a"
        assert requests[1].headers["authorization"] == "Bearer token-b"
        assert len(clients) == 2 and clients[0] is not clients[1]
        for request in requests:
            assert request.extensions["timeout"] == {"connect": 3., "read": 8., "write": 8., "pool": 3.}
    finally:
        first.auth.close()
        second.auth.close()
    assert all(client.is_closed for client in clients)
