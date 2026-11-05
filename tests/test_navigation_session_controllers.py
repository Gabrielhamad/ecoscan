"""Regression tests for tab routing, typed analysis state and component boundaries."""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from ecoscan.services.accounts import UserProfile
from ecoscan.ui.navigation import navigation_for
from ecoscan.ui.navigation_controller import ActiveNavigation, build_navigation
from ecoscan.ui.processing_configuration import ProcessingSelection
from ecoscan.ui.session_state import AnalysisSession
from ecoscan.ui.streamlit_app import main


@dataclass
class FakeTab:
    open: bool = False


@pytest.mark.parametrize("role", ["admin", "user"])
def test_navigation_preserves_existing_role_scoped_key_and_tab_order(role):
    profile = UserProfile("supabase_test", "Teste", role)
    st = MagicMock()
    spec = navigation_for(admin=profile.is_admin)
    st.tabs.return_value = [FakeTab() for _ in spec.tabs]

    routing = build_navigation(st, profile)

    st.tabs.assert_called_once_with(
        spec.tabs, key="main_navigation_" + role, on_change="rerun",
    )
    assert routing.spec == spec
    assert tuple(routing.tabs) == spec.tabs
    assert not routing.campaign_required
    assert not routing.open("missing-page")


@pytest.mark.parametrize("role", ["admin", "user"])
def test_campaign_data_is_loaded_only_for_pages_that_use_it(role):
    spec = navigation_for(admin=role == "admin")
    tabs = {name: FakeTab() for name in spec.tabs}
    routing = ActiveNavigation(spec, tabs, role)

    tabs[spec.analysis].open = True
    assert not routing.campaign_required
    tabs[spec.analysis].open = False

    for page in (spec.campaign, spec.account):
        tabs[page].open = True
        assert routing.campaign_required
        tabs[page].open = False
    if role == "admin":
        tabs["Gestão"].open = True
        assert routing.campaign_required


def test_analysis_cache_reuses_signature_and_updates_source_atomically():
    state = {}
    session = AnalysisSession(state)
    result = object()

    assert session.last_result is None
    assert not session.matches("image-a")
    session.record_analysis("image-a", result, "camera")
    assert session.matches("image-a")
    assert session.last_result is result
    assert session.last_source == "camera"

    session.record_analysis("image-b", result, "upload")
    assert not session.matches("image-a")
    assert session.matches("image-b")
    assert session.last_source == "upload"


def test_invalidation_does_not_discard_auth_or_history_on_new_image():
    state = {
        "auth_access_token": "private",
        "resolved_identity": ("test", "user"),
        "unsent_draft": "draft",
        "last_history_saved_signature": "old-image",
    }
    session = AnalysisSession(state)
    session.record_analysis("old-image", object(), "upload")
    assert session.history_saved_for("old-image")
    session.invalidate_analysis()

    assert session.last_result is None
    assert session.last_source is None
    assert not session.matches("old-image")
    assert state["auth_access_token"] == "private"
    assert state["unsent_draft"] == "draft"
    assert session.history_saved_for("old-image")


def test_history_and_ingestion_use_original_streamlit_keys():
    state = {}
    session = AnalysisSession(state)
    assert not session.history_saved_for("sha")
    session.mark_history_saved("sha")
    assert state["last_history_saved_signature"] == "sha"
    assert session.history_saved_for("sha")

    rows = [{"status": "saved"}, {"status": "invalid"}]
    session.record_ingestion(rows)
    assert session.ingestion_results == rows
    assert state["dataset_ingestion_results"] == rows


def test_processing_selection_preserves_all_custom_parameters():
    selection = ProcessingSelection(
        filter_name="gaussian",
        filter_parameters={"kernel_size": 7},
        segmentation_name="otsu",
        segmentation_parameters={"threshold": 127},
        morphology_name="opening",
        morphology_parameters={"kernel_size": 3},
        save_history=True,
    )
    options = selection.to_options()
    assert options.filter_name == "gaussian"
    assert options.filter_parameters["kernel_size"] == 7
    assert options.segmentation_name == "otsu"
    assert options.segmentation_parameters["threshold"] == 127
    assert options.morphology_name == "opening"
    assert options.morphology_parameters["kernel_size"] == 3
    assert selection.save_history


def test_main_is_a_small_coordinator_not_a_duplicate_image_service():
    source = inspect.getsource(main)
    assert len(source.splitlines()) < 160
    assert "render_analysis_page(" in source
    assert "build_navigation(" in source
    assert "AnalysisSession(" in source
    assert "analyze_waste_image" not in source
    assert 'main_navigation_' not in source
