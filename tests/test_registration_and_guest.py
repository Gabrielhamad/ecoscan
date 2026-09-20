import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from streamlit.testing.v1 import AppTest
from ecoscan.services.password_identity import register
from ecoscan.services.learning_contributions import submit_contribution
from ecoscan.services.field_testing import append_field_test_record
from ecoscan.services.accounts import append_point_transaction


class RegistrationTests(unittest.TestCase):
    def test_registration_never_uses_admin_or_accepts_session(self):
        client = MagicMock()
        with patch('ecoscan.services.password_identity._client', return_value=client):
            self.assertIsNone(register(' person@example.com ', 'long-password-123', 'long-password-123', enabled=True))
        client.auth.sign_up.assert_called_once_with({'email': 'person@example.com', 'password': 'long-password-123'})
        client.auth.admin.create_user.assert_not_called()

    def test_invalid_or_disabled_does_not_call_provider(self):
        with patch('ecoscan.services.password_identity._client') as client:
            for args in [('bad', 'long-password', 'long-password', True),
                         ('a@b.com', 'short', 'short', True),
                         ('a@b.com', 'long-password', 'different-password', True),
                         ('a@b.com', 'long-password', 'long-password', False)]:
                with self.assertRaises(ValueError):
                    register(*args[:3], enabled=args[3])
            client.assert_not_called()

    def test_guest_writes_rejected_before_storage(self):
        with self.assertRaises(ValueError):
            submit_contribution(None, None, item_id='drink_can', reporter_id='visitor_x', consent=True)
        with self.assertRaises(ValueError):
            append_field_test_record('unused', SimpleNamespace(tester_id='visitor_x'))
        with self.assertRaises(ValueError):
            append_point_transaction('unused', SimpleNamespace(user_id='visitor_x'))

    def test_guest_ui_never_queries_or_submits(self):
        with patch('ecoscan.ui.learning.citizen_contributions') as read, patch('ecoscan.ui.learning.submit_contribution') as write:
            app = AppTest.from_string('''
import streamlit as st
from types import SimpleNamespace
from ecoscan.ui.learning import render_contribution, render_citizen_protocols
profile = SimpleNamespace(id='visitor_test')
render_contribution(st, None, None, profile)
render_citizen_protocols(st, None, profile)
''').run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.button), 0)
            read.assert_not_called()
            write.assert_not_called()

    def test_registration_form_requires_consent(self):
        with patch('ecoscan.services.password_identity.register') as signup:
            app = AppTest.from_string('''
import streamlit as st
from ecoscan.ui.identity import _render_registration
_render_registration(st, {'public_signup_enabled': True})
''').run()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.error)
            signup.assert_not_called()
