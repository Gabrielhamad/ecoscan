from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ecoscan.services.accounts import (
    append_point_transaction,
    build_point_transaction,
    has_awarded_evidence,
    load_user_profiles,
    summarize_points_by_user,
    total_points_for_user,
)


class AccountsTests(unittest.TestCase):
    def test_load_user_profiles_requires_user_and_admin_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "users.json"
            path.write_text(
                json.dumps(
                    {
                        "profiles": [
                            {"id": "u1", "display_name": "Usuário", "role": "user"},
                            {"id": "a1", "display_name": "Admin", "role": "admin"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            profiles = load_user_profiles(path)

            self.assertEqual(len(profiles), 2)
            self.assertTrue(any(profile.is_admin for profile in profiles))

    def test_points_ledger_persists_user_total_and_duplicate_evidence_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "points.csv"
            transaction = build_point_transaction(
                user_id="u1",
                mission_id="m1",
                points=20,
                evidence_sha256="abc",
                detected_class="plastic",
                probability=0.81,
            )

            append_point_transaction(ledger, transaction)

            self.assertEqual(total_points_for_user(ledger, "u1"), 20)
            self.assertTrue(
                has_awarded_evidence(
                    ledger,
                    user_id="u1",
                    mission_id="m1",
                    evidence_sha256="abc",
                )
            )

    def test_summarize_points_by_user_keeps_unknown_users_visible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "points.csv"
            transaction = build_point_transaction(
                user_id="legacy",
                mission_id="m1",
                points=10,
                evidence_sha256="legacy-hash",
                detected_class="metal",
                probability=None,
            )
            append_point_transaction(ledger, transaction)

            rows = summarize_points_by_user(ledger, profiles=())

            self.assertEqual(rows[0]["user_id"], "legacy")
            self.assertEqual(rows[0]["pontos"], 10)


if __name__ == "__main__":
    unittest.main()
