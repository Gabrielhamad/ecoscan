import json
from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest

from ecoscan.config import load_config
from ecoscan.services.published_model import _CACHE, published_model


def semantic_release(tmp_path):
    config = load_config()
    config = replace(
        config,
        project_root=tmp_path,
        directories={**config.directories, "models": tmp_path / "models"},
    )
    identifier = "a" * 32
    release = {
        "id": identifier,
        "reviews": {"review": {"reviewed_at": 1, "expected_class": "plastic"}},
    }
    store = MagicMock()
    store.list.return_value = [
        {
            "id": "review",
            "reviewed_at": 1,
            "expected_class": "plastic",
            "status": "approved",
            "consent": True,
        }
    ]
    store.client.storage.from_.return_value.download.return_value = json.dumps(release).encode()
    expected = tmp_path / "models" / "remote" / identifier / "semantic.json"
    return config, store, expected


@pytest.mark.parametrize('clock', [0.0, 5.0, 100.0])
def test_current_semantic_release_is_selected(tmp_path, clock):
    config, store, expected = semantic_release(tmp_path)
    _CACHE.clear()
    with (
        patch.dict("os.environ", {"ECOSCAN_REMOTE_MODELS": "true"}),
        patch("ecoscan.services.published_model.time.monotonic", return_value=clock),
        patch("ecoscan.services.published_model.remote_store", return_value=store),
        patch("ecoscan.services.semantic_release.materialize", return_value=expected) as materialize,
    ):
        assert published_model(config) == expected
    materialize.assert_called_once()
    store.client.storage.from_.return_value.download.assert_called_once_with(
        "semantic_active.json"
    )


def test_revoked_review_blocks_current_release(tmp_path):
    config, store, _ = semantic_release(tmp_path)
    store.list.return_value[0]["consent"] = False
    _CACHE.clear()
    with (
        patch.dict("os.environ", {"ECOSCAN_REMOTE_MODELS": "true"}),
        patch("ecoscan.services.published_model.remote_store", return_value=store),
        patch("ecoscan.services.semantic_release.materialize") as materialize,
    ):
        assert published_model(config) is None
    materialize.assert_not_called()


def test_failed_cached_release_keeps_ttl_and_rechecks_after_expiry(tmp_path):
    config, store, _ = semantic_release(tmp_path)
    store.client.storage.from_.return_value.download.return_value = b'{}'
    _CACHE.clear()
    with (
        patch.dict('os.environ', {'ECOSCAN_REMOTE_MODELS': 'true'}),
        patch('ecoscan.services.published_model.remote_store', return_value=store) as remote,
        patch('ecoscan.services.published_model.time.monotonic') as clock,
        patch('ecoscan.services.semantic_release.materialize') as materialize,
    ):
        for timestamp, calls in ((0, 1), (30, 1), (61, 2)):
            clock.return_value = timestamp
            assert published_model(config) is None
            assert remote.call_count == calls
    materialize.assert_not_called()
