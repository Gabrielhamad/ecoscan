"""Photo analysis page controller with an isolated state boundary.

Performs upload, inference, result rendering and user-confirmed disposal.
All recognition rules and inference remain in dedicated domain/services.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ecoscan.app.processing_options import ProcessingPipelineOptions
from ecoscan.config import AppConfig
from ecoscan.disposal.collection_points import CollectionPoint
from ecoscan.disposal.guidance import DisposalGuidance
from ecoscan.disposal.impact import EnvironmentalImpact
from ecoscan.disposal.targets import DisposalTarget
from ecoscan.services.accounts import UserProfile
from ecoscan.services.recognition_safety import decision_for_result, decision_from_error
from ecoscan.ui.analysis_widgets import (
    _render_capture_tips,
    _render_live_camera_link,
    _render_recognition_feedback_form,
)
from ecoscan.ui.common_views import _render_user_error
from ecoscan.ui.disposal_views import (
    _render_disposal_action_panel,
    _render_public_next_action,
    _render_recognition_decision,
)
from ecoscan.ui.interaction_helpers import _input_signature, _temporary_upload
from ecoscan.ui.processing_views import (
    _render_capture_quality_advice,
    _render_photo_processing_summary,
    _render_processing_evidence,
    _render_quality_snapshot,
)
from ecoscan.ui.session_state import AnalysisSession


LOGGER = logging.getLogger(__name__)


def render_analysis_page(
    st: Any,
    analysis_tab: Any,
    config: AppConfig,
    active_profile: UserProfile,
    guidance_by_class: dict[str, DisposalGuidance],
    targets_by_class: dict[str, DisposalTarget],
    impacts_by_class: dict[str, EnvironmentalImpact],
    collection_points: list[CollectionPoint] | tuple[CollectionPoint, ...],
    pipeline_options: ProcessingPipelineOptions,
    save_history: bool,
    session: AnalysisSession,
) -> Any | None:
    """Render the mounted analysis tab and return the latest result."""
    result = session.last_result
    with analysis_tab:
        section_title = "Escanear resíduo" if not active_profile.is_admin else "Analisar resíduo"
        st.markdown(f'<div class="ecoscan-section-title">{section_title}</div>', unsafe_allow_html=True)
        if not active_profile.is_admin:
            with st.expander("Preparar uma boa foto"):
                _render_capture_tips(st)
        source_options = ["Câmera", "Imagem"] if active_profile.is_admin else ["Tirar foto", "Enviar foto"]
        source = st.radio("Entrada", source_options, horizontal=True)
        source_kind = "camera" if source in {"Câmera", "Tirar foto"} else "upload"
        if source in {"Imagem", "Enviar foto"}:
            upload_label = "Selecionar imagem do resíduo" if active_profile.is_admin else "Enviar foto do resíduo"
            uploaded_file = st.file_uploader(upload_label, type=["jpg", "jpeg", "png"])
            waiting_message = "Aguardando imagem."
        else:
            if active_profile.is_admin:
                _render_live_camera_link(st)
                uploaded_file = st.camera_input("Ligar câmera e capturar resíduo", key="camera_capture")
                waiting_message = "Aguardando captura da câmera."
            else:
                st.caption(
                    "No celular, escolha Câmera ou Galeria no seletor do aparelho. "
                    "A disponibilidade da câmera depende do navegador."
                )
                uploaded_file = st.file_uploader(
                    "Tirar ou enviar foto do resíduo",
                    type=["jpg", "jpeg", "png"],
                    key="mobile_camera_upload",
                )
                waiting_message = "Tire ou envie uma foto do resíduo para analisar."

        if uploaded_file is None:
            st.info(waiting_message)
        else:
            signature = _input_signature(uploaded_file, source_kind, pipeline_options)
            if not session.matches(signature):
                session.invalidate_analysis()
                temp_path = None
                try:
                    temp_path = _temporary_upload(uploaded_file, prefix=source_kind)
                    with st.spinner("Detectando resíduo na captura..." if source_kind == "camera" else "Detectando resíduo na imagem..."):
                        from ecoscan.services.analysis_service import analyze_waste_image
                        result = analyze_waste_image(
                            temp_path,
                            config,
                            options=pipeline_options,
                        )
                    session.record_analysis(signature, result, source_kind)
                except Exception as exc:
                    result = None
                    _render_user_error(st, exc, context="image_analysis")
                    _render_recognition_decision(st, decision_from_error(exc))
                finally:
                    if temp_path is not None:
                        try:
                            temp_path.unlink(missing_ok=True)
                        except OSError:
                            LOGGER.warning("temporary_upload_cleanup_failed")
            else:
                result = session.last_result

            if result is not None:
                should_save_history = not active_profile.id.startswith("visitor_") and (
                    bool(config.history.get("enabled", True)) or save_history)
                if should_save_history and not session.history_saved_for(signature):
                    try:
                        from ecoscan.services.history import (
                            append_history_entry,
                            build_history_entry,
                            history_path_from_config,
                        )

                        append_history_entry(
                            history_path_from_config(config),
                            build_history_entry(result, source_path=session.last_source),
                        )
                        session.mark_history_saved(signature)
                    except OSError:
                        LOGGER.warning("local_history_write_failed")
                        st.warning("A análise foi concluída, mas o histórico local não pôde ser gravado. O envio de uma contribuição é independente.")

                safety_decision = decision_for_result(result, config)
                # The suggestion can preview a category's bin, but only an
                # explicitly selected material unlocks complete instructions.
                suggested_guidance = guidance_by_class.get(safety_decision.suggested_class)
                suggested_target = targets_by_class.get(safety_decision.suggested_class)
                if not active_profile.is_admin:
                    from ecoscan.services.public_flow import build_public_next_action

                    public_action = build_public_next_action(
                        result,
                        suggested_target,
                        safety_decision,
                        suggested_material_label=(
                            suggested_guidance.display_name if suggested_guidance else None
                        ),
                    )
                    _render_public_next_action(st, public_action)

                # Keep the executed preprocessing before the recognition card so the
                # user can see exactly what image is handed to the classifier.
                from ecoscan.ui.processing_lab import render_applied_processing
                render_applied_processing(st, result.pipeline)

                left, right = st.columns([1.05, 1])
                with left:
                    st.image(result.pipeline.loaded.array, caption="Imagem analisada", width="stretch")
                with right:
                    st.markdown('<div class="ecoscan-result">', unsafe_allow_html=True)
                    _render_recognition_decision(st, safety_decision)
                    st.caption("Você pode corrigir ou confirmar o material na lista abaixo.")
                    st.markdown('<div class="ecoscan-soft-divider"></div>', unsafe_allow_html=True)
                    if active_profile.is_admin:
                        st.caption(f"Filtro aplicado: {result.pipeline.filter_result.name}")
                        st.caption(result.pipeline.element_analysis.warning)
                        _render_quality_snapshot(st, result.pipeline)
                    _render_capture_quality_advice(st, result.pipeline)
                    if active_profile.is_admin:
                        _render_photo_processing_summary(st, result.pipeline)
                    else:
                        with st.expander("Como a imagem foi tratada"):
                            _render_photo_processing_summary(st, result.pipeline)
                    st.markdown("</div>", unsafe_allow_html=True)
                    if active_profile.is_admin and st.button("Exportar evidência técnica"):
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_dir = config.directories["reports"] / "ui_exports" / timestamp
                        try:
                            from ecoscan.services.visual_report import save_pipeline_artifacts
                            save_pipeline_artifacts(result.pipeline, output_dir)
                            st.success(f"Evidência salva em {output_dir}")
                        except Exception as exc:
                            _render_user_error(st, exc, context="ui_export")

                if active_profile.is_admin:
                    _render_processing_evidence(st, result, active_profile)
                else:
                    _render_processing_evidence(
                        st,
                        result,
                        active_profile,
                        render_details_expander=True,
                    )
                _render_recognition_feedback_form(st, config, result, active_profile, guidance_by_class)

            _render_manual_material_confirmation(
                st, config, signature, guidance_by_class, targets_by_class,
                impacts_by_class, collection_points,
            )


    return result



def _render_manual_material_confirmation(
    st: Any,
    config: AppConfig,
    signature: str,
    guidance_by_class: dict[str, DisposalGuidance],
    targets_by_class: dict[str, DisposalTarget],
    impacts_by_class: dict[str, EnvironmentalImpact],
    collection_points: list[CollectionPoint] | tuple[CollectionPoint, ...],
) -> None:
    """Local human correction remains available even when image/model analysis fails."""
    st.markdown(
        '<div class="ecoscan-section-title">Confirme ou corrija o material e veja o descarte</div>',
        unsafe_allow_html=True,
    )
    confirmed_class = st.selectbox(
        "Qual material você identificou na foto?",
        [None, *config.classes],
        format_func=lambda class_id: (
            "Selecione o material (confirmação manual)"
            if class_id is None else guidance_by_class[class_id].display_name
        ),
        key=f"confirmed_disposal_{signature}",
        help="Escolha ou corrija a categoria do material. A foto não determina composição ou contaminação.",
    )
    if confirmed_class is not None:
        confirmed_guidance = guidance_by_class.get(confirmed_class)
        confirmed_target = targets_by_class.get(confirmed_class)
        confirmed_impact = impacts_by_class.get(confirmed_class)
        if confirmed_guidance is not None and confirmed_target is not None:
            st.success(f"{confirmed_guidance.display_name}: {confirmed_target.destination_title}.")
            _render_disposal_action_panel(
                st, config, confirmed_guidance, confirmed_target, confirmed_impact,
                collection_points,
            )
