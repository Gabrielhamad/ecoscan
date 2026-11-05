"""Architectural regression tests for Streamlit presentation boundaries."""
from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from ecoscan.ui import streamlit_app


UI_ROOT = Path(streamlit_app.__file__).resolve().parent
COMPONENTS = (
    "admin_views",
    "campaign_views",
    "civic_views",
    "common_views",
    "disposal_views",
    "interaction_helpers",
    "processing_views",
    "system_views",
)
BOUNDARIES = (
    ("_render_admin_tab", "admin_views"),
    ("_render_campaign_tab", "campaign_views"),
    ("_render_civic_reports_tab", "civic_views"),
    ("_render_user_error", "common_views"),
    ("_render_disposal_action_panel", "disposal_views"),
    ("_input_signature", "interaction_helpers"),
    ("_render_processing_evidence", "processing_views"),
    ("_render_model_governance", "system_views"),
)


@pytest.mark.parametrize(("symbol", "module"), BOUNDARIES)
def test_coordinator_reexports_existing_renderer_contracts(symbol, module):
    component = importlib.import_module(f"ecoscan.ui.{module}")
    assert getattr(streamlit_app, symbol) is getattr(component, symbol)


def test_specialized_views_never_depend_on_streamlit_coordinator():
    for module in COMPONENTS:
        source = (UI_ROOT / f"{module}.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = [
            name.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for name in node.names
        ] + [
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        ]
        assert not any(
            name == "ecoscan.ui.streamlit_app" or name.endswith(".streamlit_app")
            for name in imported
        ), module


def test_ui_component_dependencies_are_acyclic():
    graph = {}
    for module in COMPONENTS:
        tree = ast.parse((UI_ROOT / f"{module}.py").read_text(encoding="utf-8"))
        graph[module] = {
            node.module.rsplit(".", 1)[-1]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
            and node.module.startswith("ecoscan.ui.")
            and node.module.rsplit(".", 1)[-1] in COMPONENTS
        }
    visiting = set()
    visited = set()

    def visit(module):
        assert module not in visiting, f"Circular UI import at {module}"
        if module in visited:
            return
        visiting.add(module)
        for dependency in graph[module]:
            visit(dependency)
        visiting.remove(module)
        visited.add(module)

    for module in COMPONENTS:
        visit(module)


def test_coordinator_stays_below_monolith_budget():
    source = (UI_ROOT / "streamlit_app.py").read_text(encoding="utf-8")
    assert len(source.splitlines()) <= 1100
    assert "def main(" in source
