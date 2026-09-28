"""Pilot acceptance with simulated Auth/storage; no production credentials needed."""
import copy
import json
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest
from tests.test_contribution_store import MemoryRemote
from tests.test_learning_contributions import LearningTests
from ecoscan.services.password_identity import verified_profile
from ecoscan.services.learning_contributions import (
    citizen_contributions, contribution_package, list_contributions,
    review_contribution, submit_contribution,
)


class Pilot02Tests(unittest.TestCase):
    def profile(self, number, *, analyst=False):
        client = MagicMock()
        email = f"person{number}@example.com"
        client.auth.get_user.return_value.user = SimpleNamespace(
            id=f"00000000-0000-4000-8000-{number:012d}", email=email,
            email_confirmed_at="confirmed", user_metadata={"role": "admin"})
        with patch("ecoscan.services.password_identity._client", return_value=client):
            return verified_profile(f"token-{number}", {
                "supabase_admin_emails": [email] if analyst else []})

    def test_two_accounts_analyst_response_and_restart_preserve_protocols(self):
        fixture = LearningTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        author, other, analyst = self.profile(1), self.profile(2), self.profile(3, analyst=True)
        store = MemoryRemote()
        with patch("ecoscan.services.learning_contributions.remote_store", return_value=store):
            records = [submit_contribution(fixture.config, fixture.result, item_id="drink_can",
                       reporter_id=p.id, consent=True) for p in (author, other)]
            self.assertNotEqual(records[0]["id"], records[1]["id"])
            # Same pixels are deduplicated per author, never across accounts.
            repeated = submit_contribution(fixture.config, fixture.result, item_id="drink_can",
                                           reporter_id=author.id, consent=True)
            self.assertEqual(repeated["id"], records[0]["id"])
            self.assertEqual(len(store.rows), 2)
            before = copy.deepcopy(store.rows)
            with self.assertRaises(PermissionError):
                review_contribution(fixture.config, records[0]["id"], decision="approved", reviewer=other)
            self.assertEqual(before, store.rows)
            review_contribution(fixture.config, records[0]["id"], decision="approved",
                                reviewer=analyst, expected_revision=0, response="Confirmamos uma lata.")
            # Replace the app's local files and store client, retaining only external data.
            restarted_store = MemoryRemote()
            restarted_store.rows = copy.deepcopy(store.rows)
            restarted_store.photos = copy.deepcopy(store.photos)
        restarted = replace(fixture.config, directories={**fixture.config.directories,
                            "reports": fixture.config.project_root / "after_restart"})
        with patch("ecoscan.services.learning_contributions.remote_store", return_value=restarted_store):
            own = citizen_contributions(restarted, self.profile(1).id)
            others = citizen_contributions(restarted, self.profile(2).id)
            self.assertEqual([r["id"] for r in own], [records[0]["id"]])
            self.assertEqual([r["id"] for r in others], [records[1]["id"]])
            self.assertEqual(own[0]["response"], "Confirmamos uma lata.")
            self.assertEqual(others[0]["status"], "pending")
            for forbidden in ("reporter_id", "reviewed_by", "review_history", "image_path", "storage_key"):
                self.assertNotIn(forbidden, json.dumps(own))
            # Storage download failure never deletes the confirmed protocol.
            with patch.object(restarted_store, "image", side_effect=OSError("offline")):
                with self.assertRaises(OSError):
                    contribution_package(restarted, [restarted_store.rows[records[0]["id"]]])
            self.assertEqual(len(list_contributions(restarted)), 2)
            with self.assertRaises(ValueError):
                review_contribution(restarted, records[0]["id"], decision="rejected",
                                    reviewer=analyst, expected_revision=0)

    def identity_app(self):
        return AppTest.from_string('''
import streamlit as st
from ecoscan.ui.identity import _render_password_identity
from ecoscan.ui.learning import render_review
profile = _render_password_identity(st, {"supabase_admin_emails": ["person3@example.com"]})
render_review(st, None, profile)
''')

    def test_account_change_and_expiry_clear_private_session_data(self):
        app = self.identity_app()
        first, second = self.profile(1), self.profile(2)
        with patch("ecoscan.services.password_identity.verified_profile", return_value=first) as verify, \
             patch("ecoscan.ui.learning.list_contributions") as queue:
            app.session_state["auth_access_token"] = "first-token"
            app.run()
            for key in ("contribution_receipt_old", "review_packages", "analysis_result", "private_form"):
                app.session_state[key] = "private first-account data"
            app.session_state["auth_access_token"] = "second-token"
            verify.return_value = second
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["resolved_identity"], (second.id, "user"))
            for key in ("contribution_receipt_old", "review_packages", "analysis_result", "private_form"):
                self.assertNotIn(key, app.session_state)
            app.session_state["review_packages"] = b"private second-account photos"
            verify.side_effect = ValueError("Sessão expirada")
            app.run()
            self.assertFalse(app.exception)
            self.assertNotIn("auth_access_token", app.session_state)
            self.assertNotIn("review_packages", app.session_state)
            queue.assert_not_called()

    def test_verified_analyst_sees_queue_and_revocation_removes_it(self):
        app = self.identity_app()
        with patch("ecoscan.services.password_identity.verified_profile", return_value=self.profile(3, analyst=True)) as verify, \
             patch("ecoscan.ui.learning.list_contributions", return_value=[]) as queue, \
             patch("ecoscan.ui.learning.persistent_enabled", return_value=True):
            app.session_state["auth_access_token"] = "analyst-token"
            app.run()
            self.assertFalse(app.exception)
            queue.assert_called_once()
            self.assertTrue(any("Central de análise" in s.value for s in app.subheader))
            app.session_state["review_packages"] = b"private queue"
            verify.return_value = self.profile(3)
            app.run()
            self.assertFalse(app.exception)
            self.assertNotIn("review_packages", app.session_state)
            self.assertEqual(queue.call_count, 1)

    def test_logout_clears_all_account_state(self):
        app = self.identity_app()
        with patch("ecoscan.services.password_identity.verified_profile", return_value=self.profile(1)):
            app.session_state["auth_access_token"] = "first-token"
            app.run()
            app.session_state["contribution_receipt_old"] = "private"
            next(b for b in app.button if b.label == "Sair da conta").click().run()
            self.assertFalse(app.exception)
            self.assertNotIn("auth_access_token", app.session_state)
            self.assertNotIn("contribution_receipt_old", app.session_state)
            self.assertTrue(app.session_state["resolved_identity"][0].startswith("visitor_"))


if __name__ == "__main__":
    unittest.main()
