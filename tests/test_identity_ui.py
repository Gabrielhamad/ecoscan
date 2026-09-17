import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class IdentityUITests(unittest.TestCase):
    def app(self):
        return AppTest.from_string('''
import streamlit as st
from ecoscan.ui.identity import render_identity
profile = render_identity(st)
st.write(profile.role)
''')

    def test_admin_query_does_not_grant_access(self):
        app = self.app()
        app.query_params["profile"] = "admin_secretaria"
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["resolved_identity"][1], "user")
        self.assertTrue(app.info)

    def test_verified_admin_and_revocation(self):
        app = self.app()
        app.secrets["auth"] = {key: "test" for key in (
            "client_id", "client_secret", "cookie_secret", "redirect_uri", "server_metadata_url")}
        app.secrets["access"] = {"issuer": "trusted", "admin_emails": ["admin@example.com"]}
        claims = dict(is_logged_in=True, iss="trusted", sub="123", exp=9999999999,
                      email="admin@example.com", email_verified=True)
        with patch("streamlit.user", claims):
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["resolved_identity"][1], "admin")
            app.session_state["private_form"] = "old identity data"
            app.secrets["access"] = {"issuer": "trusted", "admin_emails": []}
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["resolved_identity"][1], "user")
            self.assertNotIn("private_form", app.session_state)
