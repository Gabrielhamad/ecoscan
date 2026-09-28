import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest
from ecoscan.services.password_identity import request_password_reset, reset_password


class RecoveryTests(unittest.TestCase):
    def client(self):
        client = MagicMock()
        user = SimpleNamespace(id="account-a", email_confirmed_at="confirmed")
        client.auth.verify_otp.return_value = SimpleNamespace(
            session=SimpleNamespace(access_token="private-token"), user=user)
        client.auth.update_user.return_value = SimpleNamespace(user=user)
        return client

    def test_request_uses_provider_and_does_not_create_account(self):
        client = self.client()
        with patch("ecoscan.services.password_identity._client", return_value=client):
            self.assertIsNone(request_password_reset(" person@example.com "))
        client.auth.reset_password_for_email.assert_called_once_with("person@example.com")
        client.auth.sign_up.assert_not_called()

    def test_invalid_request_never_calls_provider(self):
        with patch("ecoscan.services.password_identity._client") as factory:
            with self.assertRaises(ValueError):
                request_password_reset("invalid")
            factory.assert_not_called()

    def test_recovery_verifies_before_update_and_never_uses_admin(self):
        client = self.client()
        with patch("ecoscan.services.password_identity._client", return_value=client):
            reset_password("a" * 56, "new-password-123", "new-password-123")
        client.auth.verify_otp.assert_called_once_with({"token_hash": "a" * 56, "type": "recovery"})
        client.auth.update_user.assert_called_once_with({"password": "new-password-123"})
        client.auth.admin.update_user_by_id.assert_not_called()
        client.auth.sign_out.assert_called_once_with({"scope": "local"})
        self.assertEqual([c[0] for c in client.auth.method_calls],
                         ["verify_otp", "update_user", "sign_out"])

    def test_validation_does_not_consume_link(self):
        with patch("ecoscan.services.password_identity._client") as factory:
            for token, password, confirmation in [
                ("a" * 56, "short", "short"),
                ("a" * 56, "long-password", "different-password"),
                ("invalid", "long-password", "long-password"),
            ]:
                with self.assertRaises(ValueError):
                    reset_password(token, password, confirmation)
            factory.assert_not_called()

    def test_expired_replayed_and_missing_sessions_fail_closed(self):
        for failure in (RuntimeError("EXPIRED SECRET"), RuntimeError("USED SECRET"), None):
            with self.subTest(failure=failure):
                client = self.client()
                client.auth.verify_otp.side_effect = failure
                client.auth.verify_otp.return_value.session = None
                with patch("ecoscan.services.password_identity._client", return_value=client):
                    with self.assertRaises(ValueError) as caught:
                        reset_password("a" * 56, "long-password", "long-password")
                self.assertNotIn("SECRET", str(caught.exception))
                client.auth.update_user.assert_not_called()

    def test_update_failure_is_sanitized_and_session_discarded(self):
        client = self.client()
        client.auth.update_user.side_effect = RuntimeError("SECRET")
        with patch("ecoscan.services.password_identity._client", return_value=client):
            with self.assertRaises(ValueError) as caught:
                reset_password("a" * 56, "long-password", "long-password")
        self.assertNotIn("SECRET", str(caught.exception))
        client.auth.sign_out.assert_called_once()

    def test_logout_failure_does_not_hide_successful_password_change(self):
        client = self.client()
        client.auth.sign_out.side_effect = RuntimeError("offline")
        with patch("ecoscan.services.password_identity._client", return_value=client):
            self.assertIsNone(reset_password("a" * 56, "long-password", "long-password"))

    def app(self):
        return AppTest.from_string('''
import streamlit as st
from ecoscan.ui.identity import _render_password_identity
profile = _render_password_identity(st, {})
st.write("Current profile: " + profile.id)
''')

    def test_link_clears_other_account_and_requires_explicit_submission(self):
        app = self.app()
        app.session_state["auth_access_token"] = "account-b-token"
        app.session_state["review_packages"] = b"private photos"
        app.query_params["token_hash"] = "a" * 56
        app.query_params["type"] = "recovery"
        with patch("ecoscan.services.password_identity.reset_password") as reset, \
             patch("ecoscan.services.password_identity.verified_profile") as verify:
            app.run()
            self.assertFalse(app.exception)
            self.assertFalse(app.query_params)
            self.assertNotIn("auth_access_token", app.session_state)
            self.assertNotIn("review_packages", app.session_state)
            reset.assert_not_called()
            verify.assert_not_called()
            app.text_input[0].set_value("new-password-123")
            app.text_input[1].set_value("new-password-123")
            next(b for b in app.button if b.label == "Salvar nova senha").click().run()
            self.assertFalse(app.exception)
            reset.assert_called_once_with("a" * 56, "new-password-123", "new-password-123")
            self.assertNotIn("password_recovery_hash", app.session_state)
            self.assertNotIn("auth_access_token", app.session_state)
            self.assertTrue(app.success)

    def test_wrong_callback_type_cannot_become_recovery(self):
        app = self.app()
        app.query_params["token_hash"] = "a" * 56
        app.query_params["type"] = "signup"
        with patch("ecoscan.services.password_identity._client") as factory:
            app.run()
            app.text_input[0].set_value("long-password")
            app.text_input[1].set_value("long-password")
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.error)
            factory.assert_not_called()

    def test_request_cooldown_and_generic_success(self):
        with patch("ecoscan.services.password_identity.request_password_reset") as send:
            app = self.app().run()
            next(t for t in app.text_input if t.label == "E-mail da conta").set_value("a@example.com")
            next(b for b in app.button if b.label == "Enviar link de recuperação").click().run()
            self.assertTrue(app.success)
            next(b for b in app.button if b.label == "Enviar link de recuperação").click().run()
            self.assertTrue(app.warning)
            self.assertEqual(send.call_count, 1)


if __name__ == "__main__":
    unittest.main()
