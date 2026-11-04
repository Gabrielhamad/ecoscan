"""Resolve a trusted private model release; never load user-uploaded model files."""
import json
import os
import threading
import time

from ecoscan.image_processing.contracts import processing_contract
from ecoscan.services.contribution_store import remote_store

_LOCK = threading.Lock()
_CACHE = {}


def published_model(config):
    if os.environ.get("ECOSCAN_REMOTE_MODELS", "").lower() != "true" and not config.model.get("remote_models_enabled", False):
        try:
            import streamlit as st
            if st.secrets.get("training", {}).get("remote_models_enabled") is not True:
                return None
        except (FileNotFoundError, KeyError):
            return None
    key = (str(config.project_root), processing_contract(config)["sha256"])
    with _LOCK:
        previous, checked = _CACHE.get(key, (None, 0))
        if time.monotonic() - checked < 60:
            return previous
        try:
            store = remote_store()
            if store is None:
                return None
            bucket = store.client.storage.from_("ecoscan-training")
            release = json.loads(bucket.download("semantic_active.json"))
            current = {row["id"]: row for row in store.list()}
            for identifier, review in release["reviews"].items():
                row = current.get(identifier, {})
                if (row.get("status") != "approved" or row.get("consent") is not True
                        or row.get("reviewed_at") != review["reviewed_at"]
                        or row.get("expected_class") != review["expected_class"]):
                    raise ValueError("A source review was revoked or changed")
            identifier = release["id"]
            from ecoscan.services.semantic_release import materialize

            folder = config.directories["models"] / "remote" / identifier
            path = materialize(bucket, release, folder, config)
            _CACHE[key] = (path, time.monotonic())
            return path
        except Exception:
            # Fail closed: a revoked review must not keep serving the old release.
            _CACHE[key] = (None, time.monotonic())
            return None
