from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ecoscan.config import AppConfig
from ecoscan.services.operational_store import operational_store


VALID_ROLES = frozenset({"user", "admin"})


@dataclass(frozen=True)
class UserProfile:
    id: str
    display_name: str
    role: str
    organization: str = ""
    notes: str = ""
    active: bool = True

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


@dataclass(frozen=True)
class PointTransaction:
    id: str
    timestamp_utc: str
    user_id: str
    mission_id: str
    points: int
    evidence_sha256: str
    detected_class: str
    probability: float | None
    status: str
    note: str


class AccountConfigError(ValueError):
    pass


def profiles_path_from_config(config: AppConfig) -> Path:
    return config.project_root / "config" / "user_profiles.json"


def points_ledger_path_from_config(config: AppConfig) -> Path:
    return config.directories["reports"] / "accounts" / "points_ledger.csv"


def load_user_profiles(path: str | Path) -> tuple[UserProfile, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    profiles = tuple(_profile_from_payload(row) for row in payload.get("profiles", []))
    active_profiles = tuple(profile for profile in profiles if profile.active)
    if not active_profiles:
        raise AccountConfigError("At least one active user profile must be configured.")
    if not any(profile.is_admin for profile in active_profiles):
        raise AccountConfigError("At least one active admin profile must be configured.")
    return active_profiles


def fallback_profiles() -> tuple[UserProfile, ...]:
    return (
        UserProfile(
            id="usuario_demo",
            display_name="Usuário EcoScan",
            role="user",
            organization="Comunidade",
            notes="Perfil local de demonstração.",
        ),
        UserProfile(
            id="admin_secretaria",
            display_name="Gestão Ambiental",
            role="admin",
            organization="Secretaria do Meio Ambiente",
            notes="Perfil administrativo local.",
        ),
    )


def get_default_profile(profiles: tuple[UserProfile, ...], *, role: str = "user") -> UserProfile:
    for profile in profiles:
        if profile.role == role:
            return profile
    return profiles[0]


def build_point_transaction(
    *,
    user_id: str,
    mission_id: str,
    points: int,
    evidence_sha256: str,
    detected_class: str | None,
    probability: float | None,
    status: str = "awarded",
    note: str = "",
) -> PointTransaction:
    return PointTransaction(
        id=str(uuid4()),
        timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        user_id=user_id.strip(),
        mission_id=mission_id.strip(),
        points=max(0, int(points)),
        evidence_sha256=evidence_sha256.strip(),
        detected_class=(detected_class or "").strip(),
        probability=probability,
        status=status.strip() or "awarded",
        note=note.strip(),
    )


def append_point_transaction(path: str | Path, transaction: PointTransaction) -> Path:
    if not transaction.user_id or transaction.user_id.startswith("visitor_"):
        raise ValueError("Entre em uma conta para registrar pontos.")
    store = operational_store()
    if store is not None:
        store.append("points", asdict(transaction))
        return Path(path)
    ledger_path = Path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    exists = ledger_path.exists()
    with ledger_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[field.name for field in fields(PointTransaction)])
        if not exists:
            writer.writeheader()
        writer.writerow(asdict(transaction))
    return ledger_path


def read_point_transactions(
    path: str | Path,
    *,
    user_id: str | None = None,
    limit: int | None = None,
) -> list[PointTransaction]:
    store = operational_store()
    if store is not None:
        return [PointTransaction(**row) for row in store.read("points", owner=user_id, limit=limit)]
    ledger_path = Path(path)
    if not ledger_path.exists():
        return []
    rows: list[PointTransaction] = []
    allowed_fields = {field.name for field in fields(PointTransaction)}
    with ledger_path.open("r", newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            payload = {key: row.get(key, "") for key in allowed_fields}
            payload["points"] = _optional_int(payload.get("points")) or 0
            payload["probability"] = _optional_float(payload.get("probability"))
            transaction = PointTransaction(**payload)
            if user_id is None or transaction.user_id == user_id:
                rows.append(transaction)
    if limit is not None:
        return rows[-limit:]
    return rows


def total_points_for_user(path: str | Path, user_id: str) -> int:
    return sum(
        transaction.points
        for transaction in read_point_transactions(path, user_id=user_id)
        if transaction.status == "awarded"
    )


def has_awarded_evidence(
    path: str | Path,
    *,
    user_id: str,
    mission_id: str,
    evidence_sha256: str,
) -> bool:
    for transaction in read_point_transactions(path, user_id=user_id):
        if (
            transaction.status == "awarded"
            and transaction.mission_id == mission_id
            and transaction.evidence_sha256 == evidence_sha256
        ):
            return True
    return False


def summarize_points_by_user(
    path: str | Path,
    profiles: tuple[UserProfile, ...],
) -> list[dict[str, Any]]:
    profile_map = {profile.id: profile for profile in profiles}
    totals: dict[str, int] = {profile.id: 0 for profile in profiles}
    counts: dict[str, int] = {profile.id: 0 for profile in profiles}
    for transaction in read_point_transactions(path):
        if transaction.status != "awarded":
            continue
        totals[transaction.user_id] = totals.get(transaction.user_id, 0) + transaction.points
        counts[transaction.user_id] = counts.get(transaction.user_id, 0) + 1
    rows: list[dict[str, Any]] = []
    for user_id, points in sorted(totals.items(), key=lambda item: item[1], reverse=True):
        profile = profile_map.get(user_id)
        rows.append(
            {
                "user_id": user_id,
                "nome": profile.display_name if profile else user_id,
                "perfil": profile.role if profile else "desconhecido",
                "pontos": points,
                "missões_validadas": counts.get(user_id, 0),
            }
        )
    return rows


def _profile_from_payload(payload: dict[str, Any]) -> UserProfile:
    required = ["id", "display_name", "role"]
    missing = [key for key in required if key not in payload]
    if missing:
        raise AccountConfigError("User profile is missing fields: " + ", ".join(missing))
    role = str(payload["role"]).strip().lower()
    if role not in VALID_ROLES:
        raise AccountConfigError(f"Invalid user profile role: {role}")
    return UserProfile(
        id=str(payload["id"]).strip(),
        display_name=str(payload["display_name"]).strip(),
        role=role,
        organization=str(payload.get("organization", "")).strip(),
        notes=str(payload.get("notes", "")).strip(),
        active=bool(payload.get("active", True)),
    )


def _optional_float(value: Any) -> float | None:
    try:
        text = str(value or "").strip()
        return float(text) if text else None
    except ValueError:
        return None


def _optional_int(value: Any) -> int | None:
    try:
        text = str(value or "").strip()
        return int(text) if text else None
    except ValueError:
        return None
