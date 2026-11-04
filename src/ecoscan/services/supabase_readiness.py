"""Read-only checks for the Supabase schema used by the published app."""
from __future__ import annotations

from dataclasses import dataclass


TABLES = (
    "ecoscan_contributions",
    "ecoscan_points",
    "ecoscan_field_tests",
    "ecoscan_campaigns",
    "ecoscan_civic_reports",
    "ecoscan_community_audit",
)
PRIVATE_BUCKETS = ("ecoscan-contributions", "ecoscan-civic-evidence")


@dataclass(frozen=True)
class ReadinessCheck:
    item: str
    ok: bool
    detail: str


def inspect_supabase(client) -> tuple[ReadinessCheck, ...]:
    """Inspect required resources without inserting, updating or downloading data."""
    checks: list[ReadinessCheck] = []
    for table in TABLES:
        try:
            client.table(table).select("id").limit(1).execute()
        except Exception:
            checks.append(ReadinessCheck(table, False, "tabela ausente ou inacessível"))
        else:
            checks.append(ReadinessCheck(table, True, "consulta de metadados concluída"))

    try:
        buckets = client.storage.list_buckets()
    except Exception:
        checks.extend(ReadinessCheck(bucket, False, "Storage inacessível")
                      for bucket in PRIVATE_BUCKETS)
        return tuple(checks)

    by_id = {_field(bucket, "id"): bucket for bucket in buckets}
    for bucket_id in PRIVATE_BUCKETS:
        bucket = by_id.get(bucket_id)
        if bucket is None:
            checks.append(ReadinessCheck(bucket_id, False, "bucket ausente"))
        elif _field(bucket, "public") is True:
            checks.append(ReadinessCheck(bucket_id, False, "bucket está público"))
        else:
            checks.append(ReadinessCheck(bucket_id, True, "bucket privado"))
    return tuple(checks)


def _field(value, name):
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)
