import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ecoscan.services.participant_directory import registered_users


class ParticipantDirectoryTests(unittest.TestCase):
    @patch('ecoscan.services.participant_directory._client')
    def test_missing_token_never_calls_provider(self, client):
        with self.assertRaises(PermissionError):
            registered_users('', {})
        client.assert_not_called()

    @patch('ecoscan.services.participant_directory._client')
    @patch('ecoscan.services.participant_directory.verified_profile')
    def test_citizen_cannot_list_users(self, profile, client):
        profile.return_value = SimpleNamespace(is_admin=False)
        with self.assertRaises(PermissionError):
            registered_users('token', {})
        client.assert_not_called()

    @patch('ecoscan.services.participant_directory._client')
    @patch('ecoscan.services.participant_directory.verified_profile')
    def test_confirmed_account_and_pagination(self, profile, client):
        profile.return_value = SimpleNamespace(is_admin=True)
        user = SimpleNamespace(id='test-id', email='person@example.com',
            email_confirmed_at='2026-09-20', created_at='2026-09-20', last_sign_in_at=None)
        listing = client.return_value.auth.admin.list_users
        listing.side_effect = [[user] * 100, [user]]
        rows = registered_users('token', {})
        self.assertEqual(len(rows), 101)
        self.assertEqual(rows[0]['e-mail protegido'], 'p***@example.com')
        self.assertEqual(rows[0]['confirmação'], 'Confirmado')
        listing.assert_called_with(page=2, per_page=100)

    @patch('ecoscan.services.participant_directory._client')
    @patch('ecoscan.services.participant_directory.verified_profile')
    def test_error_does_not_leak_provider_details(self, profile, client):
        profile.return_value = SimpleNamespace(is_admin=True)
        client.side_effect = RuntimeError('private-secret')
        with self.assertRaises(OSError) as error:
            registered_users('token', {})
        self.assertNotIn('private-secret', str(error.exception))
