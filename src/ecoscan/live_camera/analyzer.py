from __future__ import annotations

import logging
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from ecoscan.app.pipeline import ProcessingPipelineOptions
from ecoscan.classification.runtime import ModelLoadError, RecognitionModel
from ecoscan.config import AppConfig
from ecoscan.disposal.targets import (
    DisposalTarget,
    load_disposal_targets,
)
from ecoscan.errors import build_error_payload, public_error_payload
from ecoscan.image_processing.validation import ImageValidationError
from ecoscan.services.recognition_safety import (
    RecognitionSafetyDecision, decision_for_result, decision_from_error, record_decision,
)
from ecoscan.services.analysis_service import (
    analyze_waste_image,
    load_model_bundle_for_analysis,
)
from ecoscan.live_camera.tracking import CentroidTracker, TrackedDetection


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LiveCameraSettings:
    filter_name: str = "auto"
    segmentation_name: str = "auto"
    jpeg_suffix: str = ".jpg"


class LiveCameraAnalyzer:
    """Runs EcoScan analysis on browser camera frames and tracks segmented elements."""

    def __init__(
        self,
        config: AppConfig,
        *,
        settings: LiveCameraSettings | None = None,
        model_path: str | Path | None = None,
        model_bundle: RecognitionModel | None = None,
        tracker: CentroidTracker | None = None,
    ) -> None:
        self.config = config
        self.settings = settings or LiveCameraSettings()
        self.model_bundle = model_bundle
        if self.model_bundle is None:
            try:
                self.model_bundle = load_model_bundle_for_analysis(config, model_path)
            except ModelLoadError:
                # Keep the capture/correction page available while recognition is unavailable.
                LOGGER.warning("live_model_unavailable")
        self.disposal_targets = _load_disposal_targets_for_config(config)
        self.tracker = tracker or CentroidTracker()
        self._lock = Lock()
        self._frame_index = 0

    def reset_tracking(self) -> None:
        with self._lock:
            self.tracker.reset()
            self._frame_index = 0

    def analyze_frame(self, image_bytes: bytes) -> dict[str, Any]:
        if not image_bytes:
            payload = build_error_payload(
                code="CAM-001",
                title="Frame vazio",
                message="A câmera não enviou imagem para análise.",
                action="Mantenha a câmera ativa e tente capturar o frame novamente.",
                category="camera",
            )
            decision = decision_from_error(ImageValidationError("Empty camera frame"))
            record_decision(decision)
            payload["decision"] = _decision_payload(decision)
            payload["accepted"] = False
            return payload

        start = time.perf_counter()
        temp_path = None
        analysis_started = False
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=self.settings.jpeg_suffix) as temp_file:
                temp_path = Path(temp_file.name)
                temp_file.write(image_bytes)
            with self._lock:
                self._frame_index += 1
                analysis_started = True
                result = analyze_waste_image(
                    temp_path,
                    self.config,
                    options=ProcessingPipelineOptions(
                        filter_name=self.settings.filter_name,
                        segmentation_name=self.settings.segmentation_name,
                    ),
                    model_bundle=self.model_bundle,
                )
                analysis = result.pipeline.element_analysis
                tracks = self.tracker.update(
                    analysis.elements,
                    frame_width=analysis.image_width,
                    frame_height=analysis.image_height,
                )
                frame_index = self._frame_index
        except Exception as exc:
            LOGGER.warning("live_analysis_failed error_type=%s", type(exc).__name__)
            payload = public_error_payload(exc)
            decision = decision_from_error(exc)
            if not analysis_started:
                record_decision(decision)
            payload["decision"] = _decision_payload(decision)
            payload["accepted"] = False
            return payload
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError as exc:
                    LOGGER.warning("live_temporary_frame_cleanup_failed error_type=%s", type(exc).__name__)

        # Re-resolve current policy/evidence; an attached decision is only an event snapshot.
        decision = decision_for_result(result, self.config)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        return {
            "ok": True,
            "frame_index": frame_index,
            "latency_ms": elapsed_ms,
            "model_type": result.model_type,
            "top_class": decision.suggested_class,
            "predicted_class": None,
            "accepted": False,
            "message": decision.message,
            "decision": _decision_payload(decision),
            "reliability": _reliability_payload(getattr(result, "reliability", None)),
            "guidance": None,
            "disposal_target": None,
            "suggested_target": _suggested_target_payload(
                decision.suggested_class, self.disposal_targets,
            ),
            "environmental_impact": None,
            "analysis_size": {
                "width": analysis.image_width,
                "height": analysis.image_height,
            },
            "filter": result.pipeline.metadata["filter"],
            "segmentation": result.pipeline.metadata["segmentation"],
            "quality": result.pipeline.metadata["quality"],
            "capture_quality": result.pipeline.metadata.get("capture_quality", {}),
            "elements_warning": analysis.warning,
            "detections": [
                _detection_payload(
                    track,
                    decision=decision,
                )
                for track in tracks
            ],
        }


def _decision_payload(decision: RecognitionSafetyDecision) -> dict[str, Any]:
    """Public presentation only; private reasons, evidence and scores stay server-side."""
    return {
        "status": decision.status,
        "tone": decision.tone,
        "title": decision.title,
        "message": decision.message,
        "primary_action": decision.primary_action,
        "suggested_class": decision.suggested_class,
        "requires_confirmation": decision.requires_confirmation,
        "correction_available": decision.can_correct,
    }


def _load_disposal_targets_for_config(config: AppConfig) -> dict[str, DisposalTarget]:
    project_root = getattr(config, "project_root", None)
    if project_root is None:
        return {}
    try:
        return load_disposal_targets(project_root / "config" / "disposal_targets.json")
    except Exception as exc:
        LOGGER.warning("live_disposal_targets_load_failed error_type=%s", type(exc).__name__)
        return {}


def _reliability_payload(reliability: Any | None) -> dict[str, object] | None:
    if reliability is None:
        return None
    return {
        "class_id": reliability.class_id,
        "raw_count": reliability.raw_count,
        "processed_count": reliability.processed_count,
        "target_count": reliability.target_count,
        "status": reliability.status,
        "message": reliability.message,
    }


def _suggested_target_payload(
    class_id: str | None,
    targets_by_class: dict[str, DisposalTarget],
) -> dict[str, str] | None:
    """Public preview of the category destination, without action links or scores."""
    target = targets_by_class.get(class_id) if class_id else None
    if target is None:
        return None
    return {
        "destination_title": target.destination_title,
        "bin_color_name": target.bin_color_name,
        "bin_color_hex": target.bin_color_hex,
    }


def _detection_payload(
    track: TrackedDetection,
    *,
    decision: RecognitionSafetyDecision,
) -> dict[str, Any]:
    payload = track.to_dict()
    # Regions are segmentation diagnostics, not individually classified objects.
    payload["class_id"] = None
    payload["top_class"] = None
    payload["label"] = "Região visual"
    payload["accepted"] = False
    payload["decision_tone"] = decision.tone
    return payload
