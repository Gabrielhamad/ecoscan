from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest

from ecoscan.services.password_identity import register


def test_public_registration_stores_name_without_admin_permissions():
    client = MagicMock()
    with patch("ecoscan.services.password_identity._client", return_value=client):
        register("person@example.com", "long-password-123", "long-password-123",
                 enabled=True, name=" Participante ")
    client.auth.sign_up.assert_called_once_with({
        "email": "person@example.com", "password": "long-password-123",
        "options": {"data": {"display_name": "Participante"}},
    })
    assert not client.auth.admin.mock_calls


def test_public_signup_form_requires_name_and_explains_confirmation():
    app = AppTest.from_string('''
import streamlit as st
from ecoscan.ui.identity import _render_registration
_render_registration(st, {"public_signup_enabled": True})
''').run()
    with patch("ecoscan.services.password_identity.register") as signup:
        app.button[0].click().run()
        assert app.error
        signup.assert_not_called()
        app.text_input[0].set_value("Participante")
        app.text_input[1].set_value("person@example.com")
        app.text_input[2].set_value("long-password-123")
        app.text_input[3].set_value("long-password-123")
        app.checkbox[0].check()
        app.button[0].click().run()
        assert not app.exception
        assert app.success
        signup.assert_called_once_with("person@example.com", "long-password-123",
                                       "long-password-123", enabled=True, name="Participante")


def test_recovery_cancel_opens_account_help():
    app = AppTest.from_string('''
import streamlit as st
from ecoscan.ui.identity import _render_password_identity
_render_password_identity(st, {"public_signup_enabled": True})
''')
    app.query_params["type"] = "recovery"
    app.query_params["token_hash"] = "a" * 56
    app.run()
    next(b for b in app.button if b.label.startswith("Voltar para entrar")).click().run()
    assert not app.exception
    assert app.session_state["account_help_open"] is True
    assert "password_recovery_hash" not in app.session_state
