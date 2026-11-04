from __future__ import annotations

from types import SimpleNamespace

from ecoscan.services.supabase_readiness import PRIVATE_BUCKETS, TABLES, inspect_supabase


class Query:
    def select(self, _fields):
        return self

    def limit(self, _size):
        return self

    def execute(self):
        return SimpleNamespace(data=[])


class Client:
    def __init__(self, *, failing_table=None, public_bucket=None):
        self.failing_table = failing_table
        self.public_bucket = public_bucket
        self.storage = self

    def table(self, name):
        if name == self.failing_table:
            raise RuntimeError("private backend detail")
        return Query()

    def list_buckets(self):
        return [{"id": name, "public": name == self.public_bucket} for name in PRIVATE_BUCKETS]


def test_readiness_checks_all_tables_and_private_buckets():
    checks = inspect_supabase(Client())
    assert len(checks) == len(TABLES) + len(PRIVATE_BUCKETS)
    assert all(check.ok for check in checks)


def test_readiness_reports_resource_without_leaking_backend_exception():
    checks = inspect_supabase(Client(failing_table="ecoscan_points",
                                     public_bucket="ecoscan-civic-evidence"))
    failures = {check.item: check.detail for check in checks if not check.ok}
    assert failures == {
        "ecoscan_points": "tabela ausente ou inacessível",
        "ecoscan-civic-evidence": "bucket está público",
    }
