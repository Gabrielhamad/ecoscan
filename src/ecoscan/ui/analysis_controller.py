"""Photo analysis page controller with an isolated state boundary.

Performs upload, inference, result rendering and user-confirmed disposal.
All recognition rules and inference remain in dedicated domain/services.
"""
from __future__ import annotations

import logging
import hashlib
from datetime import datetime
from typing import Any

from ecoscan.app.processing_options import ProcessingPipelineOptions
from ecoscan.config import AppConfig
from ecoscan.disposal.collection_points import CollectionPoint
from ecoscan.disposal.guidance import DisposalGuidance
from ecoscan.disposal.impact import EnvironmentalImpact
from ecoscan.disposal.targets import DisposalTarget
from ecoscan.services.accounts import UserProfile
from ecoscan.services.recognition_safety import build_recognition_safety_decision
from ecoscan.ui.analysis_widgets import (
    _render_capture_tips,
    _render_live_camera_link,
    _render_recognition_feedback_form,
)
from ecoscan.ui.common_views import _render_error_payload, _render_user_error
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
        if st.button("Nova foto", key="new_analysis"):
            session.reset_capture()
            st.rerun()
        generation = session.capture_generation
        source_options = ["Câmera", "Imagem"] if active_profile.is_admin else ["Tirar foto", "Enviar foto"]
        source = st.radio("Entrada", source_options, horizontal=True)
        st.caption("Use JPG ou PNG de até 15 MB e 40 milhões de pixels. Reduza fotos maiores antes de enviar.")
        source_kind = "camera" if source in {"Câmera", "Tirar foto"} else "upload"
        if source in {"Imagem", "Enviar foto"}:
            upload_label = "Selecionar imagem do resíduo" if active_profile.is_admin else "Enviar foto do resíduo"
            uploaded_file = st.file_uploader(upload_label, type=["jpg", "jpeg", "png"],
                                             key=f"analysis_upload_{generation}", max_upload_size=15)
            waiting_message = "Aguardando imagem."
        else:
            if active_profile.is_admin:
                _render_live_camera_link(st)
                uploaded_file = st.camera_input("Ligar câmera e capturar resíduo", key="camera_capture" if generation == 0 else f"camera_capture_{generation}")
                waiting_message = "Aguardando captura da câmera."
            else:
                st.caption(
                    "No celular, escolha Câmera ou Galeria no seletor do aparelho. "
                    "Se a câmera foi negada ou não abrir, escolha Enviar foto e use a galeria."
                )
                uploaded_file = st.file_uploader(
                    "Tirar ou enviar foto do resíduo",
                    type=["jpg", "jpeg", "png"],
                    key="mobile_camera_upload" if generation == 0 else f"mobile_camera_upload_{generation}",
                    max_upload_size=15,
                )
                waiting_message = "Tire ou envie uma foto do resíduo para analisar."

        signature = session.last_signature or "manual"
        if uploaded_file is None:
            if result is None:
                st.info(waiting_message)
            else:
                st.caption("Última análise mantida nesta sessão. Use Nova foto para começar outra captura.")
            if session.last_failure:
                _render_error_payload(st, session.last_failure)
        else:
            temp_path = None
            # Opaque fallback identity when preflight rejects before reading bytes.
            signature = "invalid_" + hashlib.sha256(
                str((uploaded_file.name, getattr(uploaded_file, "size", None), source_kind)).encode()
            ).hexdigest()
            try:
                signature = _input_signature(uploaded_file, source_kind, pipeline_options)
                retry = (result is not None or session.last_failure is not None) and st.button("Analisar novamente", key="retry_analysis")
                if retry or not session.matches(signature):
                    session.invalidate_analysis()
                    result = None
                    temp_path = _temporary_upload(uploaded_file, prefix=source_kind)
                    with st.spinner("Processando foto e consultando o modelo..."):
                        from ecoscan.services.analysis_service import analyze_waste_image
                        result = analyze_waste_image(
                            temp_path, config, options=pipeline_options, allow_model_fallback=True,
                        )
                    session.record_analysis(signature, result, source_kind)
                else:
                    result = session.last_result
                    if session.last_failure:
                        _render_error_payload(st, session.last_failure)
            except Exception as exc:
                if not session.matches(signature):
                    session.invalidate_analysis()
                result = None
                payload = _render_user_error(st, exc, context="image_analysis")
                session.record_failure(signature, source_kind, payload)
            finally:
                if temp_path is not None:
                    try:
                        temp_path.unlink(missing_ok=True)
                    except OSError:
                        LOGGER.warning("temporary_upload_cleanup_failed")

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
                except Exception:
                    LOGGER.warning("local_history_write_failed")
                    st.warning("A análise foi concluída, mas o histórico local não pôde ser gravado. O envio de uma contribuição é independente.")

            safety_decision = build_recognition_safety_decision(
                result,
                action_confidence_threshold=max(0.72, float(config.confidence_threshold)),
            )
            # The suggestion can preview a category's bin, but only an
            # explicitly selected material unlocks complete instructions.
            suggested_guidance = guidance_by_class.get(result.top_class)
            suggested_target = targets_by_class.get(result.top_class)
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
            try:
                render_applied_processing(st, result.pipeline)
            except Exception as exc:
                _render_user_error(st, exc, context="processing_evidence")

            left, right = st.columns([1.05, 1])
            with left:
                st.image(result.pipeline.loaded.array, caption="Imagem analisada", width="stretch")
            with right:
                st.markdown('<div class="ecoscan-result">', unsafe_allow_html=True)
                _render_recognition_decision(st, safety_decision)
                if suggested_guidance is not None:
                    st.subheader("Melhor correspondência: " + suggested_guidance.display_name)
                    st.caption("Hipótese automática. Confira o material na lista abaixo; a foto não confirma composição, limpeza ou conteúdo.")
                else:
                    st.subheader("Sem hipótese utilizável do modelo")
                    st.write("Você pode escolher o material manualmente ou tirar outra foto.")
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
            try:
                _render_recognition_feedback_form(st, config, result, active_profile, guidance_by_class)
            except Exception as exc:
                _render_user_error(st, exc, context="contribution_form")


        if result is not None and getattr(result, "elapsed_ms", None) is not None:
            st.caption(f"Tempo medido de processamento e reconhecimento: {result.elapsed_ms:.0f} ms.")
        st.caption("A orientação abaixo depende do material que você selecionar, mesmo sem foto ou reconhecimento. "
                   "A consulta local funciona sem o banco; mapas externos precisam de internet.")
        st.markdown(
            '<div class="ecoscan-section-title">Confirme o material e veja o descarte</div>',
            unsafe_allow_html=True,
        )
        if not guidance_by_class:
            st.warning("Orientações locais indisponíveis. Tente novamente mais tarde; não há destino confirmado.")
        confirmed_class = st.selectbox(
            "Qual material você confirmou?",
            [None, *(class_id for class_id in config.classes if class_id in guidance_by_class)],
            format_func=lambda class_id: (
                "Selecione o material (confirmação manual)"
                if class_id is None else guidance_by_class[class_id].display_name
            ),
            key=f"confirmed_disposal_{signature}",
            help="Escolha a categoria do material. A foto não determina composição ou contaminação.",
        )
        if confirmed_class is not None:
            confirmed_guidance = guidance_by_class.get(confirmed_class)
            confirmed_target = targets_by_class.get(confirmed_class)
            confirmed_impact = impacts_by_class.get(confirmed_class)
            if confirmed_guidance is not None and confirmed_target is not None:
                st.success(
                    f"Material confirmado por você: {confirmed_guidance.display_name}. "
                    f"{confirmed_target.destination_title}."
                )
                _render_disposal_action_panel(
                    st,
                    config,
                    confirmed_guidance,
                    confirmed_target,
                    confirmed_impact,
                    collection_points,
                )
            else:
                st.warning("O destino deste material está indisponível. Consulte as regras do serviço local antes de descartar.")


    return result
