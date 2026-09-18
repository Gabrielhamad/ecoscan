import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ecoscan.services.password_identity import sign_in, verified_profile


class PasswordIdentityTests(unittest.TestCase):
    def user(self, confirmed=True):
        return SimpleNamespace(id="e6d28f19-2ef6-4eb2-a35a-67de3c4c0f14",
                               email="analyst@example.com", email_confirmed_at="confirmed" if confirmed else None,
                               user_metadata={"role": "admin"})

    def test_only_verified_allowlisted_account_is_admin(self):
        client = MagicMock()
        client.auth.get_user.return_value.user = self.user()
        with patch("ecoscan.services.password_identity._client", return_value=client):
            self.assertFalse(verified_profile("token", {}).is_admin)
            allowed = {"supabase_admin_emails": ["ANALYST@example.com"]}
            self.assertTrue(verified_profile("token", allowed).is_admin)
            client.auth.get_user.return_value.user = self.user(False)
            with self.assertRaises(ValueError):
                verified_profile("token", allowed)
        client.auth.get_user.assert_called_with("token")

    def test_provider_failure_never_exposes_secret(self):
        with patch("ecoscan.services.password_identity._client", side_effect=RuntimeError("PRIVATE")):
            with self.assertRaises(ValueError) as error:
                sign_in("user@example.com", "password")
            self.assertNotIn("PRIVATE", str(error.exception))

    def test_invalid_session_cannot_authenticate(self):
        client = MagicMock()
        client.auth.get_user.side_effect = RuntimeError("expired")
        with patch("ecoscan.services.password_identity._client", return_value=client):
            with self.assertRaises(ValueError):
                verified_profile("bad", {"supabase_admin_emails": ["analyst@example.com"]})


if __name__ == "__main__":
    unittest.main()
