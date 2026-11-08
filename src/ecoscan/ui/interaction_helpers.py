"""Upload lifecycle and deterministic image-input identity."""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from ecoscan.app.processing_options import ProcessingPipelineOptions


def _check_upload(uploaded_file: Any) -> None:
    from ecoscan.image_processing.validation import ImageValidationError, MAX_IMAGE_FILE_BYTES
    if Path(uploaded_file.name or '').suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
        raise ImageValidationError('Use JPG, JPEG or PNG')
    size = getattr(uploaded_file, 'size', None)
    if size is not None and (size == 0 or size > MAX_IMAGE_FILE_BYTES):
        raise ImageValidationError('Empty upload or file exceeds 15 MB')


def _input_signature(uploaded_file: Any, source_kind: str, options: ProcessingPipelineOptions) -> str:
    from ecoscan.image_processing.contracts import PROCESSING_VERSION
    from ecoscan.image_processing.validation import ImageValidationError, MAX_IMAGE_FILE_BYTES

    _check_upload(uploaded_file)
    data = uploaded_file.getvalue()
    if not data or len(data) > MAX_IMAGE_FILE_BYTES:
        raise ImageValidationError('Empty upload or file exceeds 15 MB')
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
    from ecoscan.image_processing.validation import ImageValidationError, MAX_IMAGE_FILE_BYTES
    _check_upload(uploaded_file)
    data = uploaded_file.getbuffer()
    if not data or len(data) > MAX_IMAGE_FILE_BYTES:
        raise ImageValidationError('Empty upload or file exceeds 15 MB')
    suffix = Path(uploaded_file.name or "upload.png").suffix or ".png"
    path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, prefix=f"ecoscan_{prefix}_", suffix=suffix) as temp_file:
            path = Path(temp_file.name)
            temp_file.write(data)
        return path
    except Exception:
        if path is not None:
            path.unlink(missing_ok=True)
        raise


