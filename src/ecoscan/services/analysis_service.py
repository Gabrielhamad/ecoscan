from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, replace
from pathlib import Path

from ecoscan.app.pipeline import ProcessingPipelineOptions, ProcessingPipelineResult, run_processing_pipeline
from ecoscan.classification.runtime import (
    ModelLoadError,
    RecognitionModel,
    load_recognition_model,
    resolve_model_path,
)
from ecoscan.config import AppConfig
from ecoscan.disposal.guidance import DisposalGuidance, get_guidance, load_guidance
from ecoscan.services.dataset_reliability import ClassReliability, assess_class_reliability
from ecoscan.services.recognition_scope import restrict_prediction
from ecoscan.services.recognition_safety import (
    RecognitionSafetyDecision, decision_for_result, decision_from_error, record_decision,
)


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class WasteAnalysisResult:
    pipeline: ProcessingPipelineResult
    predicted_class: str | None
    top_class: str | None
    probability: float | None
    accepted: bool
    message: str
    guidance: DisposalGuidance | None
    probabilities: dict[str, float]
    model_type: str
    reliability: ClassReliability | None = None
    outside_scope: bool = False
    model_sha256: str = ""
    processing_compatible: bool = True
    artifact_accepted: bool = False
    artifact_threshold: float | None = None
    encoder_sha256: str = ''
    head_sha256: str = ''
    decision: RecognitionSafetyDecision | None = None


def _load_guidance_for_config(config: AppConfig) -> dict[str, DisposalGuidance]:
    return load_guidance(config.project_root / "config" / "disposal_guidance.json")


def _model_path(config: AppConfig, model_path: str | Path | None) -> Path:
    return resolve_model_path(config, model_path)


def load_model_bundle_for_analysis(
    config: AppConfig,
    model_path: str | Path | None = None,
) -> RecognitionModel:
    selected_model_path = _model_path(config, model_path)
    return load_recognition_model(config, selected_model_path)


def _predict(
    image,
    bundle: RecognitionModel,
):
    return bundle.classifier.predict_image(image)


def analyze_waste_image(
    image_path: str | Path,
    config: AppConfig,
    *,
    options: ProcessingPipelineOptions | None = None,
    model_path: str | Path | None = None,
    model_bundle: RecognitionModel | None = None,
) -> WasteAnalysisResult:
    start = time.perf_counter()
    image_path = Path(image_path)
    try:
        pipeline = run_processing_pipeline(image_path, config, options)
        selected_model_path = _model_path(config, model_path)
        # Live-camera sessions may retain a bundle from before a remote release.
        remote_release = selected_model_path.is_relative_to(config.directories["models"] / "remote")
        bundle = (
            load_recognition_model(config, selected_model_path)
            if remote_release
            else model_bundle or load_recognition_model(config, selected_model_path)
        )
        prediction = _predict(pipeline.recognition_image, bundle)
        raw_prediction = prediction
        contract = pipeline.metadata.get("recognition_preparation", {}).get("contract", {})
        compatible = bundle.classifier.metadata["processing"] == contract
        outside_scope = prediction.top_class_id not in config.classes
        if config.model.get("confirmation_required", True):
            # The current assisted release suggests a class but never confirms disposal.
            prediction = replace(prediction, class_id=None, accepted=False)
        if outside_scope:
            prediction = replace(prediction, class_id=None, top_class_id="", accepted=False)
        prediction = restrict_prediction(prediction, config.classes)
        if not compatible:
            prediction = replace(prediction, class_id=None, accepted=False)
        outside_scope = outside_scope or not prediction.top_class_id

        guidance = None
        message = "Não foi possível identificar o resíduo com segurança."
        message = "Análise assistida: confira a hipótese e confirme o material antes do descarte."
        if not compatible:
            message = "A foto foi preparada. A hipótese ainda exige confirmação: o modelo aguarda treinamento com esta preparação."
        if outside_scope:
            message = "A análise não corresponde às categorias deste piloto. Alimentos e orgânicos estão fora do escopo; não há destino confirmado."
        reliability = assess_class_reliability(config, prediction.class_id or prediction.top_class_id)
        if prediction.accepted and prediction.class_id is not None:
            guidance_by_class = _load_guidance_for_config(config)
            guidance = get_guidance(prediction.class_id, guidance_by_class)
            message = f"Categoria identificada: {guidance.display_name}."
            if reliability and not reliability.is_sufficient:
                message = f"{message} {reliability.message}"

        result = WasteAnalysisResult(
            pipeline=pipeline,
            predicted_class=prediction.class_id,
            top_class=prediction.top_class_id,
            probability=prediction.probability,
            accepted=prediction.accepted,
            message=message,
            guidance=guidance,
            probabilities=prediction.probabilities,
            model_type=bundle.model_type,
            reliability=reliability,
            outside_scope=outside_scope,
            processing_compatible=compatible,
            model_sha256=hashlib.sha256(selected_model_path.read_bytes()).hexdigest() if selected_model_path.is_file() else "unavailable",
            artifact_accepted=raw_prediction.accepted is True and raw_prediction.threshold == bundle.classifier.metadata.get('threshold'),
            artifact_threshold=bundle.classifier.metadata.get('threshold'),
            encoder_sha256=bundle.classifier.metadata.get('encoder_sha256', ''),
            head_sha256=bundle.classifier.metadata.get('head_sha256', ''),
        )
        decision = decision_for_result(result, config)
        result = replace(result, decision=decision, message=f'{decision.title}. {decision.message}')
        record_decision(decision)
    except Exception as exc:
        # Uploaded file names and exception messages may contain personal information.
        LOGGER.error("analysis_failed error_type=%s", type(exc).__name__)
        record_decision(decision_from_error(exc))
        raise

    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    LOGGER.info(
        "analysis_complete model=%s top_class=%s accepted=%s predicted=%s score=%s filter=%s segmentation=%s elapsed_ms=%s",
        result.model_type,
        result.top_class,
        result.accepted,
        result.predicted_class,
        result.probability,
        result.pipeline.metadata["filter"]["name"],
        result.pipeline.metadata["segmentation"]["name"],
        elapsed_ms,
    )
    return result


def try_analyze_waste_image(
    image_path: str | Path,
    config: AppConfig,
    *,
    options: ProcessingPipelineOptions | None = None,
    model_path: str | Path | None = None,
) -> WasteAnalysisResult:
    try:
        return analyze_waste_image(
            image_path,
            config,
            options=options,
            model_path=model_path,
        )
    except ModelLoadError:
        raise
