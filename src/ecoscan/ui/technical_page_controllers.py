"""Role-guarded technical pages, separated from application navigation.

The app coordinator decides which tab may mount; these renderers do not
perform identity management or create implicit persistence operations.
"""
from __future__ import annotations

from typing import Any

from ecoscan.config import AppConfig
from ecoscan.disposal.guidance import DisposalGuidance
from ecoscan.services.photo_requirements import PhotoRequirement
from ecoscan.ui.common_views import _class_label, _render_user_error
from ecoscan.ui.disposal_views import _render_photo_requirement_plan
from ecoscan.ui.processing_views import (
    _render_capture_quality_advice,
    _render_element_diagnostics,
    _render_filter_decision,
    _render_pipeline_diagnostics,
    _render_segmentation_decision,
)
from ecoscan.ui.session_state import AnalysisSession
from ecoscan.ui.system_views import (
    _render_acceptance_checks,
    _render_access_testing_panel,
    _render_aps_audit,
    _render_completion_panel,
    _render_dataset_readiness,
    _render_dataset_status,
    _render_delivery_pack,
    _render_dependencies,
    _render_error_catalog,
    _render_free_hosting_panel,
    _render_ingestion_results,
    _render_model_governance,
    _render_overview_strip,
)


def render_processing_details_page(
    st: Any,
    tab: Any,
    result: Any | None,
) -> None:
    with tab:
        from ecoscan.ui.processing_lab import render_processing_lab
        if result is None:
            st.info("Aguardando análise.")
        else:
            cols = st.columns(3)
            cols[0].image(result.pipeline.preprocessing.resized, caption="Redimensionada", width="stretch")
            cols[1].image(result.pipeline.filter_result.image, caption=f"Filtro: {result.pipeline.filter_result.name}", width="stretch")
            cols[2].image(result.pipeline.segmentation_result.mask, caption=f"Máscara: {result.pipeline.segmentation_result.name}", width="stretch")
            cols = st.columns(3)
            cols[0].image(result.pipeline.segmentation_result.image, caption="Segmentada", width="stretch")
            cols[1].image(result.pipeline.detection_heatmap, caption="Mapa de detecção", width="stretch")
            cols[2].image(result.pipeline.model_input_preview, caption="Entrada do modelo", width="stretch")
            render_processing_lab(st, result.pipeline)
            st.markdown('<div class="ecoscan-section-title">Qualidade da captura</div>', unsafe_allow_html=True)
            _render_capture_quality_advice(st, result.pipeline)
            st.markdown('<div class="ecoscan-section-title">Decisão de filtragem</div>', unsafe_allow_html=True)
            _render_filter_decision(st, result.pipeline)
            st.markdown('<div class="ecoscan-section-title">Decisão de segmentação</div>', unsafe_allow_html=True)
            _render_segmentation_decision(st, result.pipeline)
            st.markdown('<div class="ecoscan-section-title">Elementos visuais segmentados</div>', unsafe_allow_html=True)
            cols = st.columns([0.95, 1.05])
            cols[0].image(result.pipeline.element_overlay, caption="Componentes detectados na máscara", width="stretch")
            with cols[1]:
                _render_element_diagnostics(st, result.pipeline)
            st.markdown('<div class="ecoscan-section-title">Métricas de qualidade da imagem</div>', unsafe_allow_html=True)
            _render_pipeline_diagnostics(st, result.pipeline)
            st.markdown('<div class="ecoscan-section-title">Metadados técnicos</div>', unsafe_allow_html=True)
            st.json(result.pipeline.metadata)


def render_dataset_page(
    st: Any,
    tab: Any,
    config: AppConfig,
    guidance_by_class: dict[str, DisposalGuidance],
    requirements_by_class: dict[str, PhotoRequirement],
    class_chips: str,
    session: AnalysisSession,
) -> None:
    with tab:
        from ecoscan.services.dataset_ingestion import (
            IncomingImage,
            ingest_uploaded_images,
            ingestion_manifest_path_from_config,
        )

        st.markdown('<div class="ecoscan-section-title">Adicionar fotos à base</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="ecoscan-note">As fotos entram primeiro na base bruta por classe. '
            "Antes do treino final, elas devem passar por revisão, curadoria e divisão de treino/validação/teste.</div>",
            unsafe_allow_html=True,
        )
        upload_col, context_col = st.columns([1.1, 0.9])
        with upload_col:
            target_class = st.selectbox(
                "Classe de destino",
                config.classes,
                format_func=lambda class_id: _class_label(class_id, guidance_by_class),
            )
            dataset_uploads = st.file_uploader(
                "Selecionar fotos",
                type=[extension.lstrip(".") for extension in sorted(config.allowed_extensions)],
                accept_multiple_files=True,
                key="dataset_uploads",
            )
            source_note = st.text_input("Origem do lote", placeholder="ex.: fotos do grupo - setembro")
            save_disabled = not dataset_uploads
            if save_disabled:
                st.caption("Selecione uma ou mais fotos para liberar o envio para a base bruta.")
            if st.button("Salvar na base bruta", disabled=save_disabled):
                incoming = [
                    IncomingImage(
                        name=uploaded.name,
                        data=uploaded.getvalue(),
                        source_note=source_note or "streamlit-upload",
                    )
                    for uploaded in dataset_uploads
                ]
                try:
                    results = ingest_uploaded_images(config, target_class, incoming)
                    session.record_ingestion([result.__dict__ for result in results])
                    saved_count = sum(1 for result in results if result.status == "saved")
                    st.success(f"{saved_count} imagem(ns) adicionada(s) à base bruta.")
                except Exception as exc:
                    _render_user_error(st, exc, context="dataset_ingestion")
        with context_col:
            st.markdown('<div class="ecoscan-section-title">Classes ativas</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="ecoscan-chip-row">{class_chips}</div>',
                unsafe_allow_html=True,
            )
            st.caption(f"Registro de uploads: {ingestion_manifest_path_from_config(config)}")
            st.markdown('<div class="ecoscan-section-title">Plano de coleta</div>', unsafe_allow_html=True)
            _render_photo_requirement_plan(st, requirements_by_class.get(target_class))

        _render_ingestion_results(st, session.ingestion_results)
        st.markdown('<div class="ecoscan-section-title">Prontidão para treino</div>', unsafe_allow_html=True)
        _render_dataset_readiness(st, config)
        st.markdown('<div class="ecoscan-section-title">Resumo da base de imagens</div>', unsafe_allow_html=True)
        _render_dataset_status(st, config, guidance_by_class)


def render_conclusion_page(
    st: Any,
    tab: Any,
    config: AppConfig,
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    with tab:
        st.markdown('<div class="ecoscan-section-title">Conclusão e prontidão final</div>', unsafe_allow_html=True)
        _render_completion_panel(st, config)
        _render_model_governance(st, config, guidance_by_class)


def render_system_page(
    st: Any,
    tab: Any,
    config: AppConfig,
) -> None:
    with tab:
        _render_overview_strip(st, config)
        st.markdown('<div class="ecoscan-section-title">Acesso e rodada de testes</div>', unsafe_allow_html=True)
        _render_access_testing_panel(st)
        st.markdown('<div class="ecoscan-section-title">Hospedagem gratuita HTTPS</div>', unsafe_allow_html=True)
        _render_free_hosting_panel(st, config)
        st.markdown('<div class="ecoscan-section-title">Auditoria técnica</div>', unsafe_allow_html=True)
        _render_aps_audit(st, config)
        st.markdown('<div class="ecoscan-section-title">Relatório técnico</div>', unsafe_allow_html=True)
        if st.button("Gerar relatório consolidado"):
            try:
                from ecoscan.services.academic_report import write_academic_report

                report_path = write_academic_report(config)
                st.success(f"Relatório gerado em {report_path}")
            except Exception as exc:
                _render_user_error(st, exc, context="academic_report")
        st.markdown('<div class="ecoscan-section-title">Validação do sistema</div>', unsafe_allow_html=True)
        _render_acceptance_checks(st, config)
        st.markdown('<div class="ecoscan-section-title">Mensagens de erro do sistema</div>', unsafe_allow_html=True)
        _render_error_catalog(st)
        st.markdown('<div class="ecoscan-section-title">Pacote técnico</div>', unsafe_allow_html=True)
        _render_delivery_pack(st, config)
        st.markdown('<div class="ecoscan-section-title">Ambiente local</div>', unsafe_allow_html=True)
        _render_dependencies(st)


