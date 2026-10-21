"""Resolve a trusted private model release; never load user-uploaded model files."""
import hashlib
import json
import os
import re
import threading
import time

from ecoscan.image_processing.contracts import contract_path, model_processing_compatible, processing_contract
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
            release = json.loads(bucket.download("active.json"))
            current = {row["id"]: row for row in store.list()}
            for identifier, review in release["reviews"].items():
                row = current.get(identifier, {})
                if (row.get("status") != "approved" or row.get("consent") is not True
                        or row.get("reviewed_at") != review["reviewed_at"]
                        or row.get("expected_class") != review["expected_class"]):
                    raise ValueError("A source review was revoked or changed")
            identifier = release["id"]
            if not re.fullmatch(r"[a-f0-9]{32}", identifier):
                raise ValueError("Invalid release")
            if (release["model_key"] != f"runs/{identifier}/model.joblib"
                    or release["contract_key"] != f"runs/{identifier}/contract.json"
                    or release["processing_sha256"] != key[1]
                    or set(release["classes"]) != set(config.classes)):
                raise ValueError("Incompatible release")
            folder = config.directories["models"] / "remote" / identifier
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / "model.joblib"
            if not path.exists():
                data = bucket.download(release["model_key"])
                if hashlib.sha256(data).hexdigest() != release["sha256"]:
                    raise ValueError("Invalid checksum")
                temporary = folder / "download.tmp"
                temporary.write_bytes(data)
                temporary.replace(path)
                contract_path(path).write_bytes(bucket.download(release["contract_key"]))
            if not model_processing_compatible(path, processing_contract(config)):
                raise ValueError("Incompatible processing")
            _CACHE[key] = (path, time.monotonic())
            return path
        except Exception:
            # Fail closed: a revoked review must not keep serving the old release.
            _CACHE[key] = (None, time.monotonic())
            return None
