"""Upload lifecycle and deterministic image-input identity."""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from ecoscan.app.processing_options import ProcessingPipelineOptions


def _input_signature(uploaded_file: Any, source_kind: str, options: ProcessingPipelineOptions) -> str:
    from ecoscan.image_processing.contracts import PROCESSING_VERSION

    data = uploaded_file.getvalue()
    payload = {
        "processing_version": PROCESSING_VERSION,
        "source_kind": source_kind,
        "name": uploaded_file.name,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "options": {
            "filter_name": options.filter_name,
            "filter_parameters": options.filter_parameters or {},
            "segmentation_name": options.segmentation_name,
            "segmentation_parameters": options.segmentation_parameters or {},
            "morphology_name": options.morphology_name,
            "morphology_parameters": options.morphology_parameters or {},
        },
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _temporary_upload(uploaded_file: Any, prefix: str = "upload") -> Path:
    suffix = Path(uploaded_file.name or "upload.png").suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, prefix=f"ecoscan_{prefix}_", suffix=suffix) as temp_file:
        temp_file.write(uploaded_file.getbuffer())
        return Path(temp_file.name)


