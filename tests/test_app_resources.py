from dataclasses import replace
import json
from pathlib import Path

from ecoscan.config import load_config
from ecoscan.ui.app_resources import load_app_resources
from ecoscan.ui.navigation import navigation_for


def test_reference_data_is_cached_and_invalidated_by_file_change(tmp_path):
    source = load_config()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    for path in (source.project_root / "config").glob("*.json"):
        (config_dir / path.name).write_bytes(path.read_bytes())
    config = replace(source, project_root=tmp_path)
    first = load_app_resources(config)
    assert first is load_app_resources(config)
    assert first.guidance_by_class and first.collection_points and first.profiles

    path = config_dir / "disposal_guidance.json"
    payload = json.loads(path.read_text())
    payload["plastic"]["display_name"] = "Material alterado no teste"
    path.write_text(json.dumps(payload))
    second = load_app_resources(config)
    assert second is not first
    assert any(item.display_name == "Material alterado no teste"
               for item in second.guidance_by_class.values())


def test_missing_reference_isolated_without_hiding_other_data(tmp_path):
    source = load_config()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    for path in (source.project_root / "config").glob("*.json"):
        if path.name != "disposal_targets.json":
            (config_dir / path.name).write_bytes(path.read_bytes())
    resources = load_app_resources(replace(source, project_root=tmp_path))
    assert resources.targets_by_class == {}
    assert resources.guidance_by_class
    assert resources.collection_points


def test_navigation_labels_are_unique_and_keep_analysis_first():
    citizen = navigation_for(admin=False)
    admin = navigation_for(admin=True)
    for spec in (citizen, admin):
        assert spec.tabs[0] == spec.analysis
        assert len(spec.tabs) == len(set(spec.tabs))
        assert {spec.analysis, spec.campaign, spec.report, spec.collection, spec.account} <= set(spec.tabs)
