from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from ecoscan.services.engagement import LESSONS, award_once, award_quiz
from ecoscan.services.accounts import read_point_transactions
from ecoscan.services.campaigns import campaign_from_payload, load_campaign
from ecoscan.config import PROJECT_ROOT


@pytest.fixture(autouse=True)
def local_store():
    with patch("ecoscan.services.accounts.operational_store", return_value=None):
        yield


def test_correct_quiz_once_per_account(tmp_path):
    path = tmp_path / "ledger.csv"
    result = award_quiz(path, user_id="user1", material="oil", answer=LESSONS["oil"]["answer"])
    assert result.points == 10
    with pytest.raises(ValueError, match="já"):
        award_quiz(path, user_id="user1", material="oil", answer=LESSONS["oil"]["answer"])
    award_quiz(path, user_id="user2", material="oil", answer=LESSONS["oil"]["answer"])
    assert len(read_point_transactions(path)) == 2


@pytest.mark.parametrize("user, answer", [("visitor_a", 1), ("user1", 0), ("user1", True)])
def test_wrong_answer_and_visitor_do_not_save(tmp_path, user, answer):
    path = tmp_path / "ledger.csv"
    with pytest.raises(ValueError):
        award_quiz(path, user_id=user, material="oil", answer=answer)
    assert not path.exists()


def test_no_fallback_or_success_on_remote_failure(tmp_path):
    with patch("ecoscan.services.engagement.read_point_transactions", side_effect=OSError("offline")):
        with pytest.raises(OSError):
            award_quiz(tmp_path / "ledger.csv", user_id="u1", material="oil", answer=1)
    assert not (tmp_path / "ledger.csv").exists()


def test_stable_key_for_database_unique_constraint(tmp_path):
    with patch("ecoscan.services.engagement.read_point_transactions", return_value=[]), patch("ecoscan.services.engagement.append_point_transaction") as append:
        for _ in range(2):
            award_once(tmp_path / "ledger.csv", user_id="u1", mission_id="m1", points=20, note="education")
    assert append.call_args_list[0].args[1].evidence_sha256 == append.call_args_list[1].args[1].evidence_sha256


def test_legacy_reward_not_promised_as_available():
    payload = asdict(load_campaign(PROJECT_ROOT / "config" / "campaigns.json"))
    import json
    payload = json.loads(json.dumps(payload))
    for reward in payload["rewards"]:
        reward.pop("kind")
    assert all(r.kind == "partner_planned" for r in campaign_from_payload(payload).rewards)


def test_visitor_can_practice_without_saving():
    app = AppTest.from_string('''
import streamlit as st
from ecoscan.ui.education import render_education
from ecoscan.config import PROJECT_ROOT
render_education(st, PROJECT_ROOT)
''').run()
    app.selectbox[0].set_value("oil").run()
    app.radio[0].set_value(1).run()
    app.button[0].click().run()
    assert not app.exception
    assert any("Entre em sua conta" in x.value for x in app.info)
