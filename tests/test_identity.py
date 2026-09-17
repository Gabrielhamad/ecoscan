import unittest

from ecoscan.services.identity import resolve_identity


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.claims = dict(is_logged_in=True, iss="https://accounts.google.com",
                           sub="123", exp=2000, email="gestor@example.com",
                           email_verified=True, name="Gestor")
        self.access = dict(issuer="https://accounts.google.com",
                           admin_emails=["GESTOR@example.com"])

    def resolve(self, claims=None, access=None, visitor="a"):
        return resolve_identity(self.claims if claims is None else claims,
                                self.access if access is None else access,
                                visitor, now=1000)

    def test_authorized_verified_account_is_admin(self):
        self.assertTrue(self.resolve().is_admin)

    def test_missing_or_untrusted_claims_cannot_elevate(self):
        for changes in [dict(email_verified=False), dict(email_verified="true"),
                        dict(email="other@example.com"), dict(iss="other"),
                        dict(is_logged_in=False), dict(exp=1000), dict(exp="invalid"),
                        dict(exp=float("nan")), dict(sub="")]:
            with self.subTest(changes=changes):
                self.assertFalse(self.resolve({**self.claims, **changes}).is_admin)

    def test_empty_or_malformed_access_denies_admin(self):
        for access in [{}, {**self.access, "admin_emails": "gestor@example.com"}]:
            self.assertFalse(self.resolve(access=access).is_admin)

    def test_visitors_are_isolated_and_never_admin(self):
        first = self.resolve({}, visitor="a")
        second = self.resolve({}, visitor="b")
        self.assertNotEqual(first.id, second.id)
        self.assertFalse(first.is_admin)

    def test_identity_stable_across_sessions_not_email_based(self):
        self.assertEqual(self.resolve(visitor="a").id, self.resolve(visitor="b").id)
        self.assertEqual(self.resolve().id, self.resolve({**self.claims, "email": "new"}).id)
        self.assertNotEqual(self.resolve().id, self.resolve({**self.claims, "sub": "456"}).id)


if __name__ == "__main__":
    unittest.main()
