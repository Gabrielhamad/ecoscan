import hashlib
import json
from dataclasses import replace
from unittest.mock import MagicMock, patch

from ecoscan.config import load_config
from ecoscan.image_processing.contracts import processing_contract
from ecoscan.services.published_model import _CACHE, published_model


def setup_release(tmp_path):
    config = load_config()
    config = replace(config, project_root=tmp_path,
                     directories={**config.directories, "models": tmp_path / "models"})
    data = b"trusted-model-bytes"
    identifier = "a" * 32
    digest = hashlib.sha256(data).hexdigest()
    contract = processing_contract(config)
    release = {"id": identifier, "model_key": f"runs/{identifier}/model.joblib",
               "contract_key": f"runs/{identifier}/contract.json", "sha256": digest,
               "processing_sha256": contract["sha256"], "classes": list(config.classes),
               "reviews": {"review": {"reviewed_at": 1, "expected_class": "plastic"}}}
    objects = {"active.json": json.dumps(release).encode(), release["model_key"]: data,
               release["contract_key"]: json.dumps({"model_sha256": digest, "processing": contract}).encode()}
    store = MagicMock()
    store.list.return_value = [{"id": "review", "reviewed_at": 1, "expected_class": "plastic",
                                "status": "approved", "consent": True}]
    store.client.storage.from_.return_value.download.side_effect = lambda key: objects[key]
    return config, store, objects, release


def test_release_requires_matching_hash_and_contract(tmp_path):
    config, store, objects, release = setup_release(tmp_path)
    _CACHE.clear()
    with patch.dict("os.environ", {"ECOSCAN_REMOTE_MODELS": "true"}), \
         patch("ecoscan.services.published_model.remote_store", return_value=store):
        path = published_model(config)
    assert path.read_bytes() == b"trusted-model-bytes"


def test_corrupt_release_is_not_loaded(tmp_path):
    config, store, objects, release = setup_release(tmp_path)
    objects[release["model_key"]] = b"modified"
    _CACHE.clear()
    with patch.dict("os.environ", {"ECOSCAN_REMOTE_MODELS": "true"}), \
         patch("ecoscan.services.published_model.remote_store", return_value=store):
        assert published_model(config) is None


def test_revoked_review_blocks_release(tmp_path):
    config, store, _, _ = setup_release(tmp_path)
    store.list.return_value[0]["status"] = "rejected"
    _CACHE.clear()
    with patch.dict("os.environ", {"ECOSCAN_REMOTE_MODELS": "true"}), \
         patch("ecoscan.services.published_model.remote_store", return_value=store):
        assert published_model(config) is None
