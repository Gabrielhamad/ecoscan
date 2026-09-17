from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, replace
from pathlib import Path

from ecoscan.app.pipeline import ProcessingPipelineOptions, ProcessingPipelineResult, run_processing_pipeline
from ecoscan.classification.inference import (
    BaselineModelBundle,
    KerasModelBundle,
    ModelLoadError,
    VisualKnnModelBundle,
    VisualSvmModelBundle,
    load_baseline_model,
    load_keras_model,
    load_visual_knn_model,
    load_visual_svm_model,
    predict_with_baseline,
    predict_with_keras,
    predict_with_visual_knn,
    predict_with_visual_svm,
)
from ecoscan.classification.material_rules import MaterialRuleDecision, apply_material_rules
from ecoscan.config import AppConfig
from ecoscan.disposal.guidance import DisposalGuidance, get_guidance, load_guidance
from ecoscan.services.dataset_reliability import ClassReliability, assess_class_reliability
from ecoscan.services.recognition_scope import restrict_prediction


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
    material_rule: MaterialRuleDecision | None = None
    outside_scope: bool = False
    model_sha256: str = ""


def _load_guidance_for_config(config: AppConfig) -> dict[str, DisposalGuidance]:
    return load_guidance(config.project_root / "config" / "disposal_guidance.json")


def _visual_model_path(config: AppConfig) -> Path:
    return config.directories["models"] / "vision_classifier.npz"


def _visual_svm_model_path(config: AppConfig) -> Path:
    return config.directories["models"] / "vision_svm_classifier.joblib"


def _model_path(config: AppConfig, model_path: str | Path | None) -> Path:
    if model_path:
        return Path(model_path)
    final_model_path = config.project_root / str(config.model.get("output_path", "models/ecoscan_transfer.keras"))
    if final_model_path.exists():
        return final_model_path
    visual_model_path = _visual_model_path(config)
    if visual_model_path.exists():
        return visual_model_path
    visual_svm_model_path = _visual_svm_model_path(config)
    if visual_svm_model_path.exists():
        return visual_svm_model_path
    return config.directories["models"] / "baseline_classifier.json"


def _load_bundle_for_path(
    config: AppConfig,
    model_path: Path,
) -> BaselineModelBundle | KerasModelBundle | VisualKnnModelBundle | VisualSvmModelBundle:
    if model_path.suffix.lower() == ".keras":
        class_names_path = config.project_root / str(config.model.get("class_names_path", "models/class_names.json"))
        return load_keras_model(
            model_path,
            class_names_path=class_names_path,
            threshold=config.confidence_threshold,
        )
    if model_path.suffix.lower() == ".npz":
        return load_visual_knn_model(model_path)
    if model_path.suffix.lower() in {".joblib", ".pkl"}:
        return load_visual_svm_model(model_path)
    return load_baseline_model(model_path)


def load_model_bundle_for_analysis(
    config: AppConfig,
    model_path: str | Path | None = None,
) -> BaselineModelBundle | KerasModelBundle | VisualKnnModelBundle | VisualSvmModelBundle:
    selected_model_path = _model_path(config, model_path)
    return _load_bundle_for_path(config, selected_model_path)


def _predict(
    config: AppConfig,
    image,
    bundle: BaselineModelBundle | KerasModelBundle | VisualKnnModelBundle | VisualSvmModelBundle,
):
    if isinstance(bundle, KerasModelBundle):
        return predict_with_keras(image, bundle, config.image_size)
    if isinstance(bundle, VisualSvmModelBundle):
        return predict_with_visual_svm(image, bundle)
    if isinstance(bundle, VisualKnnModelBundle):
        return predict_with_visual_knn(image, bundle)
    return predict_with_baseline(image, bundle)


def analyze_waste_image(
    image_path: str | Path,
    config: AppConfig,
    *,
    options: ProcessingPipelineOptions | None = None,
    model_path: str | Path | None = None,
    model_bundle: BaselineModelBundle | KerasModelBundle | VisualKnnModelBundle | VisualSvmModelBundle | None = None,
) -> WasteAnalysisResult:
    start = time.perf_counter()
    image_path = Path(image_path)
    try:
        pipeline = run_processing_pipeline(image_path, config, options)
        selected_model_path = _model_path(config, model_path)
        bundle = model_bundle or _load_bundle_for_path(config, selected_model_path)
        prediction = _predict(config, pipeline.segmentation_result.image, bundle)
        outside_scope = prediction.top_class_id not in config.classes
        prediction, material_rule = apply_material_rules(
            prediction,
            image=pipeline.preprocessing.resized,
            mask=pipeline.segmentation_result.mask,
            element_analysis=pipeline.element_analysis,
        )
        if outside_scope:
            prediction = replace(prediction, class_id=None, top_class_id="", accepted=False)
            material_rule = None
        prediction = restrict_prediction(prediction, config.classes)
        outside_scope = outside_scope or not prediction.top_class_id

        guidance = None
        message = "Não foi possível identificar o resíduo com segurança."
        if outside_scope:
            message = "A análise não corresponde às categorias deste piloto. Alimentos e orgânicos estão fora do escopo; não há destino confirmado."
        reliability = assess_class_reliability(config, prediction.class_id or prediction.top_class_id)
        if prediction.accepted and prediction.class_id is not None:
            guidance_by_class = _load_guidance_for_config(config)
            guidance = get_guidance(prediction.class_id, guidance_by_class)
            message = f"Categoria identificada: {guidance.display_name}."
            if reliability and not reliability.is_sufficient:
                message = f"{message} {reliability.message}"
            if material_rule is not None:
                message = f"{message} Validação visual aplicada: {material_rule.reason}."

        result = WasteAnalysisResult(
            pipeline=pipeline,
            predicted_class=prediction.class_id,
            top_class=prediction.top_class_id,
            probability=prediction.probability,
            accepted=prediction.accepted,
            message=message,
            guidance=guidance,
            probabilities=prediction.probabilities,
            model_type=f"{bundle.model_type}+material_rules" if material_rule else bundle.model_type,
            reliability=reliability,
            material_rule=material_rule,
            outside_scope=outside_scope,
            model_sha256=hashlib.sha256(selected_model_path.read_bytes()).hexdigest() if selected_model_path.is_file() else "unavailable",
        )
    except Exception:
        LOGGER.exception("analysis_failed image=%s", image_path)
        raise

    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    LOGGER.info(
        "analysis_complete image=%s model=%s top_class=%s accepted=%s predicted=%s score=%s filter=%s segmentation=%s elapsed_ms=%s",
        image_path,
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
