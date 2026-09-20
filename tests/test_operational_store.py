import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from dataclasses import asdict
import os

from ecoscan.services.operational_store import OperationalStore, operational_store
from ecoscan.services.accounts import build_point_transaction, append_point_transaction, read_point_transactions
from ecoscan.services.field_testing import build_field_test_record, append_field_test_record, read_field_test_records


class OperationalStoreTests(unittest.TestCase):
    def test_rollout_disabled_does_not_connect(self):
        with patch.dict(os.environ, {"ECOSCAN_OPERATIONS_ENABLED": "false"}), patch(
            "ecoscan.services.operational_store.remote_store"
        ) as remote:
            self.assertIsNone(operational_store())
            remote.assert_not_called()

    def test_enabled_without_credentials_fails_closed(self):
        with patch.dict(os.environ, {"ECOSCAN_OPERATIONS_ENABLED": "true"}), patch(
            "ecoscan.services.operational_store.remote_store", return_value=None
        ):
            with self.assertRaises(OSError):
                operational_store()

    def test_field_test_rejects_oversized_note(self):
        with self.assertRaises(ValueError):
            build_field_test_record(tester_id="u", tester_name="User", expected_class="metal",
                                    result_status="errou", device_kind="celular", capture_mode="foto",
                                    note="x" * 601)

    def test_records_roundtrip_uses_remote_not_paths(self):
        store = MagicMock()
        transaction = build_point_transaction(user_id="supabase_test", mission_id="m1", points=10,
                                              evidence_sha256="sha", detected_class="metal", probability=.8)
        store.read.return_value = [asdict(transaction)]
        with patch("ecoscan.services.accounts.operational_store", return_value=store):
            append_point_transaction("nonexistent/ledger.csv", transaction)
            self.assertEqual([transaction], read_point_transactions("another/ledger.csv", user_id="supabase_test"))
        store.append.assert_called_once_with("points", asdict(transaction))
        store.read.assert_called_once_with("points", owner="supabase_test", limit=None)

    def test_field_test_uses_same_database_across_paths(self):
        store = MagicMock()
        record = build_field_test_record(tester_id="u", tester_name="User", expected_class="metal",
                                         result_status="errou", device_kind="celular", capture_mode="foto")
        store.read.return_value = [asdict(record)]
        with patch("ecoscan.services.field_testing.operational_store", return_value=store):
            append_field_test_record("unused.csv", record)
            self.assertEqual([record], read_field_test_records("different.csv", tester_id="u", limit=8))

    def test_pagination_and_chronological_order(self):
        client = MagicMock()
        query = client.table.return_value.select.return_value
        query.order.return_value = query
        query.eq.return_value = query
        query.range.return_value = query
        query.execute.side_effect = [SimpleNamespace(data=[{"record": {"id": str(i)}} for i in range(500)]),
                                     SimpleNamespace(data=[{"record": {"id": "oldest"}}])]
        rows = OperationalStore(client).read("points", owner="user")
        self.assertEqual(len(rows), 501)
        self.assertEqual(rows[0]["id"], "oldest")
        self.assertEqual(query.range.call_count, 2)
        query.eq.assert_called_with("user_id", "user")

    def test_outage_is_not_an_empty_history(self):
        client = MagicMock()
        client.table.side_effect = RuntimeError("secret")
        with self.assertRaises(OSError) as error:
            OperationalStore(client).read("field_tests")
        self.assertNotIn("secret", str(error.exception))

    def test_visitor_cannot_receive_permanent_points(self):
        with self.assertRaises(ValueError):
            OperationalStore(MagicMock()).append("points", {"user_id": "visitor_123"})

    def test_database_conflict_is_reported_without_second_insert(self):
        client = MagicMock()
        class Conflict(Exception):
            code = "23505"
        client.table.return_value.insert.return_value.execute.side_effect = Conflict()
        with self.assertRaises(ValueError):
            OperationalStore(client).append("field_tests", {"id": "id", "tester_id": "user"})
        self.assertEqual(client.table.return_value.insert.call_count, 1)
