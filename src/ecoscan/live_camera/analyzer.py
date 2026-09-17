from __future__ import annotations

import logging
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from ecoscan.app.pipeline import ProcessingPipelineOptions
from ecoscan.classification.inference import (
    BaselineModelBundle,
    KerasModelBundle,
    VisualKnnModelBundle,
    VisualSvmModelBundle,
)
from ecoscan.config import AppConfig
from ecoscan.disposal.guidance import DisposalGuidance
from ecoscan.disposal.impact import (
    EnvironmentalImpact,
    get_environmental_impact,
    load_environmental_impacts,
)
from ecoscan.disposal.targets import (
    DisposalTarget,
    build_map_search_url,
    get_disposal_target,
    load_disposal_targets,
)
from ecoscan.errors import build_error_payload
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
        model_bundle: BaselineModelBundle | KerasModelBundle | VisualKnnModelBundle | VisualSvmModelBundle | None = None,
        tracker: CentroidTracker | None = None,
    ) -> None:
        self.config = config
        self.settings = settings or LiveCameraSettings()
        self.model_bundle = model_bundle or load_model_bundle_for_analysis(config, model_path)
        self.disposal_targets = _load_disposal_targets_for_config(config)
        self.environmental_impacts = _load_environmental_impacts_for_config(config)
        self.tracker = tracker or CentroidTracker()
        self._lock = Lock()
        self._frame_index = 0

    def reset_tracking(self) -> None:
        with self._lock:
            self.tracker.reset()
            self._frame_index = 0

    def analyze_frame(self, image_bytes: bytes) -> dict[str, Any]:
        if not image_bytes:
            return build_error_payload(
                code="CAM-001",
                title="Frame vazio",
                message="A câmera não enviou imagem para análise.",
                action="Mantenha a câmera ativa e tente capturar o frame novamente.",
                category="camera",
            )

        start = time.perf_counter()
        with tempfile.NamedTemporaryFile(delete=False, suffix=self.settings.jpeg_suffix) as temp_file:
            temp_file.write(image_bytes)
            temp_path = Path(temp_file.name)

        try:
            with self._lock:
                self._frame_index += 1
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
        finally:
            temp_path.unlink(missing_ok=True)

        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        return {
            "ok": True,
            "frame_index": frame_index,
            "latency_ms": elapsed_ms,
            "model_type": result.model_type,
            "top_class": result.top_class,
            "predicted_class": result.predicted_class,
            "accepted": result.accepted,
            "probability": result.probability,
            "probabilities": result.probabilities,
            "message": result.message,
            "reliability": _reliability_payload(getattr(result, "reliability", None)),
            "guidance": _guidance_payload(result.guidance),
            "disposal_target": _target_payload(
                result.predicted_class,
                accepted=result.accepted,
                targets_by_class=self.disposal_targets,
            ),
            "environmental_impact": _impact_payload(
                result.predicted_class,
                accepted=result.accepted,
                impacts_by_class=self.environmental_impacts,
            ),
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
                    class_id=result.predicted_class,
                    top_class=result.top_class,
                    probability=result.probability,
                    accepted=result.accepted,
                    guidance=result.guidance,
                )
                for track in tracks
            ],
        }


def _load_disposal_targets_for_config(config: AppConfig) -> dict[str, DisposalTarget]:
    project_root = getattr(config, "project_root", None)
    if project_root is None:
        return {}
    try:
        return load_disposal_targets(project_root / "config" / "disposal_targets.json")
    except Exception as exc:
        LOGGER.warning("live_disposal_targets_load_failed detail=%s", exc)
        return {}


def _load_environmental_impacts_for_config(config: AppConfig) -> dict[str, EnvironmentalImpact]:
    project_root = getattr(config, "project_root", None)
    if project_root is None:
        return {}
    try:
        return load_environmental_impacts(project_root / "config" / "environmental_impacts.json")
    except Exception as exc:
        LOGGER.warning("live_environmental_impacts_load_failed detail=%s", exc)
        return {}


def _guidance_payload(guidance: DisposalGuidance | None) -> dict[str, str] | None:
    if guidance is None:
        return None
    return {
        "display_name": guidance.display_name,
        "environmental_category": guidance.environmental_category,
        "guidance": guidance.guidance,
        "educational_note": guidance.educational_note,
    }


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


def _impact_payload(
    class_id: str | None,
    *,
    accepted: bool,
    impacts_by_class: dict[str, EnvironmentalImpact],
) -> dict[str, Any] | None:
    if not accepted or not class_id:
        return None
    try:
        impact = get_environmental_impact(class_id, impacts_by_class)
    except Exception:
        return None
    return {
        "impact_title": impact.impact_title,
        "risk_level": impact.risk_level,
        "risk_label": impact.risk_label,
        "bad_disposal_risks": list(impact.bad_disposal_risks),
        "positive_action": impact.positive_action,
        "source_label": impact.source_label,
        "source_url": impact.source_url,
    }


def _target_payload(
    class_id: str | None,
    *,
    accepted: bool,
    targets_by_class: dict[str, DisposalTarget],
) -> dict[str, Any] | None:
    if not accepted or not class_id:
        return None
    try:
        target = get_disposal_target(class_id, targets_by_class)
    except Exception:
        return None
    return {
        "destination_title": target.destination_title,
        "destination_type": target.destination_type,
        "bin_color_name": target.bin_color_name,
        "bin_color_hex": target.bin_color_hex,
        "search_query": target.search_query,
        "map_url": build_map_search_url(target.search_query, "perto de mim"),
        "preparation_steps": list(target.preparation_steps),
        "attention_note": target.attention_note,
    }


def _detection_payload(
    track: TrackedDetection,
    *,
    class_id: str | None,
    top_class: str | None,
    probability: float | None,
    accepted: bool,
    guidance: DisposalGuidance | None,
) -> dict[str, Any]:
    payload = track.to_dict()
    payload["class_id"] = class_id
    payload["top_class"] = top_class
    payload["label"] = guidance.display_name if accepted and guidance else "incerto"
    payload["score"] = probability
    payload["accepted"] = accepted
    return payload
