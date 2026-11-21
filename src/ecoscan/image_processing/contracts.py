"""Bind a trained artifact to the RGB preparation used to produce its features."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ecoscan.config import AppConfig


PROCESSING_VERSION = "rgb-preserved-v2"


def recognition_processing_contract(config: AppConfig) -> dict[str, Any]:
    """Released preparation uses configuration defaults, never didactic selections.

    Keep the rgb-preserved-v2 payload unchanged: existing heads and seeds remain
    compatible. Configuration drift still requires validation of a new profile.
    """
    return processing_contract(config)


def processing_contract_matches(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    """Check both the declared profile and its checksum before inference."""
    try:
        digest = hashlib.sha256(json.dumps(actual['profile'], sort_keys=True).encode()).hexdigest()
        return actual['sha256'] == digest and expected == actual
    except (KeyError, TypeError, ValueError):
        return False


def processing_contract(config, *, filter_name=None, filter_parameters=None):
    payload = {
        "version": PROCESSING_VERSION,
        "working_max_dimension": int(config.processing.get("max_dimension", 640)),
        "image_size": list(config.image_size),
        "padding_rgb": int(config.processing.get("padding_rgb", 127)),
        "filter": filter_name or config.filters.get("default", "auto"),
        "parameters": filter_parameters or {},
        "filters_config": config.filters,
        "mask_applied_to_classifier": False,
    }
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return {"profile": payload, "sha256": fingerprint}


def contract_path(model_path: Path) -> Path:
    return model_path.with_suffix(model_path.suffix + ".processing.json")


def write_model_contract(model_path: Path, contract: dict) -> Path:
    path = contract_path(model_path)
    path.write_text(json.dumps({"model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
                                "processing": contract}, indent=2), encoding="utf-8")
    return path


def model_processing_compatible(model_path: Path, contract: dict) -> bool:
    try:
        saved = json.loads(contract_path(model_path).read_text(encoding="utf-8"))
        return (saved["processing"]["sha256"] == contract["sha256"]
                and saved["model_sha256"] == hashlib.sha256(model_path.read_bytes()).hexdigest())
    except (OSError, ValueError, KeyError, TypeError):
        return False
