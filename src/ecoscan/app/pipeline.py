from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ecoscan.config import AppConfig
from ecoscan.image_processing.adaptive_filters import apply_adaptive_filter_pipeline
from ecoscan.image_processing.capture_quality import CaptureQualityAssessment, assess_capture_quality
from ecoscan.image_processing.filters import FilterResult, apply_filter
from ecoscan.image_processing.image_io import LoadedImage, load_rgb_image
from ecoscan.image_processing.preprocessing import (
    PreprocessResult,
    model_input_preview,
    prepare_model_input,
)
from ecoscan.image_processing.quality import (
    ImageQualityMetrics,
    analyze_image_quality,
)
from ecoscan.segmentation.elements import (
    ElementAnalysis,
    analyze_visual_elements,
    draw_detection_heatmap,
    draw_element_overlay,
)
from ecoscan.segmentation.adaptive import segment_image_adaptive
from ecoscan.segmentation.methods import SegmentationResult, segment_image


@dataclass(frozen=True)
class ProcessingPipelineOptions:
    filter_name: str = "auto"
    filter_parameters: dict[str, Any] | None = None
    segmentation_name: str = "auto"
    segmentation_parameters: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProcessingPipelineResult:
    loaded: LoadedImage
    preprocessing: PreprocessResult
    quality_original: ImageQualityMetrics
    filter_result: FilterResult
    quality_filtered: ImageQualityMetrics
    segmentation_result: SegmentationResult
    element_analysis: ElementAnalysis
    element_overlay: np.ndarray
    detection_heatmap: np.ndarray
    capture_quality: CaptureQualityAssessment
    model_input_preview: np.ndarray
    metadata: dict[str, Any]


def _configured_filter_parameters(config: AppConfig, name: str) -> dict[str, Any]:
    return dict(config.filters.get(name, {}))


def _adaptive_filter_parameters(config: AppConfig) -> dict[str, Any]:
    parameters = dict(config.filters)
    auto_parameters = dict(parameters.get("auto", {}))
    method_parameters = dict(auto_parameters.get("method_parameters", {}))
    for filter_name in ("none", "gaussian", "median", "bilateral", "clahe"):
        method_parameters.setdefault(filter_name, _configured_filter_parameters(config, filter_name))
    auto_parameters["method_parameters"] = method_parameters
    parameters["auto"] = auto_parameters
    return parameters


def _configured_segmentation_parameters(config: AppConfig, name: str) -> dict[str, Any]:
    return dict(config.segmentation.get(name, {}))


def _adaptive_segmentation_parameters(config: AppConfig) -> dict[str, Any]:
    parameters = _configured_segmentation_parameters(config, "auto")
    method_parameters = dict(parameters.get("method_parameters", {}))
    for method_name in ("otsu", "hsv_color", "grabcut"):
        method_parameters.setdefault(method_name, _configured_segmentation_parameters(config, method_name))
    parameters["method_parameters"] = method_parameters
    return parameters


def run_processing_pipeline(
    image_path: str | Path,
    config: AppConfig,
    options: ProcessingPipelineOptions | None = None,
) -> ProcessingPipelineResult:
    selected_options = options or ProcessingPipelineOptions(
        filter_name=str(config.filters.get("default", "auto")),
        segmentation_name=str(config.segmentation.get("default", "auto")),
    )
    loaded = load_rgb_image(
        image_path,
        allowed_extensions=config.allowed_extensions,
        min_size=config.min_image_size,
    )

    preprocessing = prepare_model_input(loaded.array, config.image_size)
    quality_original = analyze_image_quality(preprocessing.resized)

    requested_filter = selected_options.filter_name.lower().strip()
    selected_filter = requested_filter
    filter_decision = {
        "requested": requested_filter,
        "selected": selected_filter,
        "reason": "filtro definido manualmente",
        "selected_sequence": [selected_filter],
        "candidates": [],
        "skipped": [],
    }
    if requested_filter == "auto":
        adaptive_filter = apply_adaptive_filter_pipeline(
            preprocessing.resized,
            _adaptive_filter_parameters(config),
            quality=quality_original,
            overrides=selected_options.filter_parameters,
        )
        filter_result = adaptive_filter.filter_result
        filter_decision = adaptive_filter.decision
    else:
        filter_parameters = _configured_filter_parameters(config, selected_filter)
        filter_parameters.update(selected_options.filter_parameters or {})
        filter_result = apply_filter(
            preprocessing.resized,
            selected_filter,
            filter_parameters,
        )
    quality_filtered = analyze_image_quality(filter_result.image)

    requested_segmentation = selected_options.segmentation_name.lower().strip()
    segmentation_decision = {
        "requested": requested_segmentation,
        "selected": requested_segmentation,
        "reason": "segmentação definida manualmente",
        "candidates": [],
        "skipped": [],
    }
    if requested_segmentation == "auto":
        segmentation_parameters = _adaptive_segmentation_parameters(config)
        segmentation_parameters.update(selected_options.segmentation_parameters or {})
        adaptive_result = segment_image_adaptive(
            filter_result.image,
            segmentation_parameters,
            quality=quality_filtered,
        )
        segmentation_result = adaptive_result.segmentation
        segmentation_decision = adaptive_result.decision
    else:
        segmentation_parameters = _configured_segmentation_parameters(config, requested_segmentation)
        segmentation_parameters.update(selected_options.segmentation_parameters or {})
        segmentation_result = segment_image(
            filter_result.image,
            requested_segmentation,
            segmentation_parameters,
        )
    element_analysis = analyze_visual_elements(segmentation_result.mask)
    element_overlay = draw_element_overlay(filter_result.image, element_analysis)
    detection_heatmap = draw_detection_heatmap(preprocessing.resized, segmentation_result.mask, element_analysis)
    capture_quality = assess_capture_quality(quality_original, quality_filtered, element_analysis)

    model_preprocess = prepare_model_input(segmentation_result.image, config.image_size)
    preview = model_input_preview(model_preprocess.normalized)

    return ProcessingPipelineResult(
        loaded=loaded,
        preprocessing=preprocessing,
        quality_original=quality_original,
        filter_result=filter_result,
        quality_filtered=quality_filtered,
        segmentation_result=segmentation_result,
        element_analysis=element_analysis,
        element_overlay=element_overlay,
        detection_heatmap=detection_heatmap,
        capture_quality=capture_quality,
        model_input_preview=preview,
        metadata={
            "image_path": str(Path(image_path)),
            "original_size": [loaded.info.width, loaded.info.height],
            "target_size": list(config.image_size),
            "quality": {
                "before_filter": quality_original.to_dict(),
                "after_filter": quality_filtered.to_dict(),
            },
            "filter": {
                "decision": filter_decision,
                "name": filter_result.name,
                "parameters": filter_result.parameters,
                "dependency": filter_result.dependency,
                "explanation": filter_result.explanation,
            },
            "segmentation": {
                "decision": segmentation_decision,
                "name": segmentation_result.name,
                "parameters": segmentation_result.parameters,
                "dependency": segmentation_result.dependency,
                "foreground_ratio": segmentation_result.foreground_ratio,
                "explanation": segmentation_result.explanation,
            },
            "elements": element_analysis.to_dict(),
            "visual_explanation": {
                "heatmap": "Mapa de calor gerado a partir da máscara de segmentação; áreas quentes indicam pixels considerados parte do resíduo.",
                "overlay": "Caixas destacam componentes visuais relevantes encontrados na máscara.",
            },
            "capture_quality": capture_quality.to_dict(),
            "model_input_shape": list(model_preprocess.model_input.shape),
        },
    )
