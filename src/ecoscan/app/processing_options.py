"""Lightweight image controls; importing them never loads image engines."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from ecoscan.config import AppConfig


@dataclass(frozen=True)
class ProcessingPipelineOptions:
    filter_name: str = "auto"
    filter_parameters: dict[str, Any] | None = None
    segmentation_name: str = "auto"
    segmentation_parameters: dict[str, Any] | None = None
    morphology_name: str = "open_close"
    morphology_parameters: dict[str, Any] | None = None


def default_processing_options(config: AppConfig) -> ProcessingPipelineOptions:
    morphology = dict(config.segmentation.get("morphology", {}))
    operation = str(morphology.pop("default", "open_close"))
    return ProcessingPipelineOptions(
        filter_name=str(config.filters.get("default", "auto")),
        segmentation_name=str(config.segmentation.get("default", "auto")),
        morphology_name=operation,
        morphology_parameters=morphology,
    )
