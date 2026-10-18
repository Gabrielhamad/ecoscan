"""Cross-service journeys with isolated storage and a simulated auth provider.

These tests do not assert SMTP delivery, production RLS or physical-device use.
"""
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import numpy as np
import pytest

from ecoscan.config import PROJECT_ROOT, load_config
from ecoscan.disposal.collection_points import (
    load_collection_points, filter_collection_points,
    build_collection_point_directions_url,
)
from ecoscan.services.accounts import UserProfile, total_points_for_user
from ecoscan.services.engagement import LESSONS, award_quiz
from ecoscan.services.learning_contributions import (
    submit_contribution, review_contribution, citizen_contributions,
    list_contributions,
)
from ecoscan.services.password_identity import register, verified_profile


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr("ecoscan.services.accounts.operational_store", lambda: None)
    monkeypatch.setattr("ecoscan.services.learning_contributions.remote_store", lambda: None)
    return replace(load_config(), project_root=tmp_path, directories={
        "reports": tmp_path / "reports", "models": tmp_path / "models"})


def photo():
    return SimpleNamespace(
        predicted_class="glass", top_class="glass", probability=.6, accepted=True,
        model_type="test", model_sha256="isolated-model",
        pipeline=SimpleNamespace(
            loaded=SimpleNamespace(array=np.zeros((32, 32, 3), dtype=np.uint8)),
            filter_result=SimpleNamespace(name="gaussian"),
            segmentation_result=SimpleNamespace(name="otsu")))


def test_registration_confirmation_and_account_switching(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr("ecoscan.services.password_identity._client", lambda: client)
    users = {name: SimpleNamespace(id=str(UUID(int=index)), email=f"{name}@example.com",
             email_confirmed_at=None, user_metadata={"role": "admin"})
             for index, name in enumerate(("alice", "bob", "analyst"), start=1)}
    client.auth.get_user.side_effect = lambda token: SimpleNamespace(user=users[token])
    access = {"supabase_admin_emails": ["analyst@example.com"]}
    for name, user in users.items():
        register(user.email, "Test-only-password-123", "Test-only-password-123", enabled=True)
        with pytest.raises(ValueError):
            verified_profile(name, access)
        # Confirmation is simulated at the provider boundary, not by the app.
        user.email_confirmed_at = "2026-01-01T00:00:00Z"
    profiles = [verified_profile(name, access) for name in ("alice", "bob", "analyst", "alice")]
    assert profiles[0].id == profiles[3].id
    assert profiles[0].id != profiles[1].id
    assert [p.is_admin for p in profiles] == [False, False, True, False]
    assert client.auth.sign_up.call_count == 3


def test_report_review_and_points_survive_new_session(isolated):
    alice, bob = "supabase_alice", "supabase_bob"
    first = submit_contribution(isolated, photo(), item_id="drink_can", reporter_id=alice, consent=True)
    duplicate = submit_contribution(isolated, photo(), item_id="drink_can", reporter_id=alice, consent=True)
    second = submit_contribution(isolated, photo(), item_id="drink_can", reporter_id=bob, consent=True)
    assert duplicate["id"] == first["id"]
    assert second["id"] != first["id"]
    fresh_session = replace(isolated)
    assert len(list_contributions(fresh_session)) == 2
    with pytest.raises(PermissionError):
        review_contribution(fresh_session, first["id"], decision="approved",
                            reviewer=UserProfile(alice, "Alice", "user"))
    review_contribution(fresh_session, first["id"], decision="approved",
                        reviewer=UserProfile("analyst_a", "Analyst A", "admin"),
                        response="Material revisado", expected_revision=0)
    with pytest.raises(ValueError):
        review_contribution(fresh_session, first["id"], decision="rejected",
                            reviewer=UserProfile("analyst_b", "Analyst B", "admin"),
                            expected_revision=0)
    receipt = citizen_contributions(replace(isolated), alice)
    assert len(receipt) == 1
    assert receipt[0]["status"] == "approved"
    assert receipt[0]["response"] == "Material revisado"
    assert "reviewed_by" not in receipt[0]
    assert citizen_contributions(fresh_session, bob)[0]["status"] == "pending"
    ledger = isolated.directories["reports"] / "journey_points.csv"
    for user in (alice, bob):
        award_quiz(ledger, user_id=user, material="metal", answer=LESSONS["metal"]["answer"])
        with pytest.raises(ValueError):
            award_quiz(ledger, user_id=user, material="metal", answer=LESSONS["metal"]["answer"])
        assert total_points_for_user(ledger, user) == 10
    points = filter_collection_points(
        load_collection_points(PROJECT_ROOT / "config" / "collection_points.json"),
        class_id="metal", city_query="São Paulo")
    assert points
    assert all(p.city == "São Paulo" and "metal" in p.accepted_classes for p in points)
    assert "destination=" in build_collection_point_directions_url(points[0])


@pytest.mark.parametrize("reporter, consent", [("visitor_test", True), ("supabase_alice", False)])
def test_visitor_or_missing_consent_never_persists(isolated, reporter, consent):
    with pytest.raises(ValueError):
        submit_contribution(isolated, photo(), item_id="drink_can", reporter_id=reporter, consent=consent)
    assert list_contributions(isolated) == []
