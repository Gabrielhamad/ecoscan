"""Processing diagnostics and evidence views.

Presentation only: all image processing runs in ecoscan.app and ecoscan.image_processing.
Streamlit is injected as a parameter; importing this module does not start the UI.
"""
from __future__ import annotations

import html
from typing import Any

from ecoscan.services.accounts import UserProfile


def _format_percent(value: float | None) -> str:
    if value is None:
        return "indisponível"
    return f"{value * 100:.1f}%"


def _render_quality_snapshot(st: Any, pipeline: Any) -> None:
    quality = pipeline.quality_original
    items = [
        ("exposição", quality.exposure_status),
        ("contraste", quality.contrast_status),
        ("foco", quality.focus_status),
        ("filtro", pipeline.filter_result.name),
        ("segmentação", pipeline.segmentation_result.name),
    ]
    pills = "".join(
        '<span class="ecoscan-mini-pill">'
        f"{html.escape(label)} <small>{html.escape(value)}</small>"
        "</span>"
        for label, value in items
    )
    st.markdown(f'<div class="ecoscan-quality-strip">{pills}</div>', unsafe_allow_html=True)


def _render_capture_quality_advice(st: Any, pipeline: Any) -> None:
    assessment = pipeline.metadata.get("capture_quality", {})
    if not assessment:
        return
    status = str(assessment.get("status", "good"))
    actions = assessment.get("actions") or []
    action_items = "".join(f"<li>{html.escape(str(action))}</li>" for action in actions[:3])
    st.markdown(
        f"""
        <div class="ecoscan-capture-advice {html.escape(status)}">
            <div class="ecoscan-capture-title">
                <span>{html.escape(str(assessment.get("title", "Qualidade da captura")))}</span>
                <span class="ecoscan-capture-score">{html.escape(str(assessment.get("score", "-")))} / 100</span>
            </div>
            <p>{html.escape(str(assessment.get("message", "")))}</p>
            <ul>{action_items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_photo_processing_summary(st: Any, pipeline: Any) -> None:
    filter_meta = pipeline.metadata.get("filter", {})
    filter_decision = filter_meta.get("decision") or {}
    segmentation_meta = pipeline.metadata.get("segmentation", {})
    segmentation_decision = segmentation_meta.get("decision") or {}
    capture_quality = pipeline.metadata.get("capture_quality", {})
    element_analysis = pipeline.element_analysis
    capture_label = str(capture_quality.get("title") or "Qualidade da captura")
    capture_score = capture_quality.get("score")
    if capture_score is not None:
        capture_label = f"{capture_label} ({capture_score}/100)"

    rows = [
        (
            "Filtro experimental",
            str(filter_decision.get("selected") or filter_meta.get("name") or pipeline.filter_result.name),
            str(filter_decision.get("reason") or filter_meta.get("explanation") or ""),
        ),
        (
            "Segmentação experimental",
            str(segmentation_decision.get("selected") or segmentation_meta.get("name") or pipeline.segmentation_result.name),
            str(segmentation_decision.get("reason") or segmentation_meta.get("explanation") or ""),
        ),
        (
            "Elementos",
            f"{element_analysis.significant_count} elemento(s) relevante(s)",
            str(element_analysis.warning),
        ),
        (
            "Captura",
            capture_label,
            str(capture_quality.get("message") or ""),
        ),
    ]
    rendered_rows = "".join(
        "<div class=\"ecoscan-tech-row\">"
        f"<div class=\"ecoscan-tech-label\">{html.escape(label)}</div>"
        f"<div class=\"ecoscan-tech-value\">{html.escape(value)}"
        f"<span class=\"ecoscan-tech-reason\">{html.escape(reason)}</span></div>"
        "</div>"
        for label, value, reason in rows
    )
    st.markdown(
        '<div class="ecoscan-tech-summary">'
        '<div class="ecoscan-tech-summary-title">Processamento experimental e qualidade da captura</div>'
        f"{rendered_rows}"
        "</div>",
        unsafe_allow_html=True,
    )


def _method_chip(label: str, value: str) -> str:
    return (
        '<div class="ecoscan-method-chip">'
        f"<span>{html.escape(label)}</span>"
        f"<strong>{html.escape(value)}</strong>"
        "</div>"
    )


def _render_processing_evidence(
    st: Any,
    result: Any,
    active_profile: UserProfile,
    *,
    render_details_expander: bool = True,
) -> None:
    from ecoscan.ui.processing_lab import render_processing_lab
    pipeline = result.pipeline
    filter_name = pipeline.filter_result.name
    segmentation_name = pipeline.segmentation_result.name
    element_count = pipeline.element_analysis.significant_count
    model_name = result.model_type
    accepted_label = "classificação sugerida" if result.accepted else "reconhecimento incerto"

    method_chips = "".join(
        [
            _method_chip("Filtro", filter_name),
            _method_chip("Segmentação experimental", segmentation_name),
            _method_chip("Elementos", f"{element_count} detectado(s)"),
            _method_chip("Modelo", model_name),
        ]
    )
    st.markdown(
        f"""
        <section class="ecoscan-evidence-panel">
            <div class="ecoscan-evidence-head">
                <div>
                    <strong>Evidência visual da análise</strong>
                    <span>Antes, depois e mapa de detecção gerados para esta imagem específica.</span>
                </div>
                <div class="ecoscan-evidence-badge">{html.escape(accepted_label)}</div>
            </div>
            <div class="ecoscan-method-strip">{method_chips}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    primary_cols = st.columns(2)
    primary_cols[0].image(pipeline.loaded.array, caption="Antes: imagem original enviada", width="stretch")
    primary_cols[1].image(
        pipeline.detection_heatmap,
        caption="Máscara em cores: região selecionada pela segmentação, não confiança do modelo",
        width="stretch",
    )

    detail_cols = st.columns(3)
    detail_cols[0].image(
        pipeline.filter_result.image,
        caption=f"Depois do filtro adaptativo: {filter_name}",
        width="stretch",
    )
    detail_cols[1].image(
        pipeline.segmentation_result.image,
        caption=f"Objeto segmentado: {segmentation_name}",
        width="stretch",
    )
    detail_cols[2].image(
        pipeline.element_overlay,
        caption="Componentes da máscara; não equivalem a objetos reconhecidos",
        width="stretch",
    )

    def render_details() -> None:
        stage_cols = st.columns(3)
        stage_cols[0].image(pipeline.preprocessing.resized, caption="1. Redimensionamento", width="stretch")
        stage_cols[1].image(pipeline.filter_result.image, caption=f"2. Filtragem: {filter_name}", width="stretch")
        stage_cols[2].image(
            pipeline.segmentation_result.mask,
            caption=f"3. Máscara: {segmentation_name}",
            width="stretch",
        )
        stage_cols = st.columns(3)
        stage_cols[0].image(pipeline.segmentation_result.image, caption="4. Imagem segmentada", width="stretch")
        stage_cols[1].image(pipeline.model_input_preview, caption="5. Prévia normalizada; a preparação final depende do classificador", width="stretch")
        stage_cols[2].image(pipeline.element_overlay, caption="6. Componentes visuais", width="stretch")

        render_processing_lab(st, pipeline)
        _render_photo_processing_summary(st, pipeline)
        _render_filter_decision(st, pipeline)
        _render_segmentation_decision(st, pipeline)
        _render_element_diagnostics(st, pipeline)

    if render_details_expander:
        with st.expander("Ver etapas completas e decisão técnica", expanded=active_profile.is_admin):
            render_details()
    else:
        render_details()


def _render_pipeline_diagnostics(st: Any, pipeline: Any) -> None:
    quality_rows = [
        {
            "etapa": "antes do filtro",
            "brilho médio": pipeline.quality_original.brightness_mean,
            "contraste": pipeline.quality_original.contrast,
            "nitidez": pipeline.quality_original.sharpness,
            "densidade de bordas": pipeline.quality_original.edge_density,
            "exposição": pipeline.quality_original.exposure_status,
            "foco": pipeline.quality_original.focus_status,
            "recomendação": pipeline.quality_original.recommendation,
        },
        {
            "etapa": "após filtro",
            "brilho médio": pipeline.quality_filtered.brightness_mean,
            "contraste": pipeline.quality_filtered.contrast,
            "nitidez": pipeline.quality_filtered.sharpness,
            "densidade de bordas": pipeline.quality_filtered.edge_density,
            "exposição": pipeline.quality_filtered.exposure_status,
            "foco": pipeline.quality_filtered.focus_status,
            "recomendação": pipeline.quality_filtered.recommendation,
        },
    ]
    st.dataframe(quality_rows, width="stretch", hide_index=True)


def _render_filter_decision(st: Any, pipeline: Any) -> None:
    decision = pipeline.metadata.get("filter", {}).get("decision", {})
    if not decision:
        return
    selected = decision.get("selected", pipeline.filter_result.name)
    issues = decision.get("quality_issues") or []
    issue_text = ", ".join(str(issue) for issue in issues)
    st.markdown(
        f"""
        <div class="ecoscan-note">
            <strong>Filtragem escolhida:</strong> {html.escape(str(selected))}<br>
            {html.escape(str(decision.get("reason", "")))}<br>
            <span class="ecoscan-muted">Diagnóstico: {html.escape(issue_text)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    candidates = decision.get("candidates") or []
    if candidates:
        st.dataframe(candidates, width="stretch", hide_index=True)
    parameters = pipeline.filter_result.parameters
    steps = parameters.get("steps") or [{"parameters": parameters}]
    for step in steps:
        kernel = step.get("parameters", {}).get("kernel_2d")
        if kernel is not None:
            with st.expander("Convolução gaussiana aplicada"):
                st.dataframe(kernel, width="stretch", hide_index=True)
                st.caption("Pesos aplicados à vizinhança de cada pixel, separadamente nos canais RGB. A soma dos pesos é 1.")
    skipped = decision.get("skipped") or []
    if skipped:
        st.caption("Sequências ignoradas por indisponibilidade técnica:")
        st.dataframe(skipped, width="stretch", hide_index=True)


def _render_segmentation_decision(st: Any, pipeline: Any) -> None:
    decision = pipeline.metadata.get("segmentation", {}).get("decision", {})
    if not decision:
        return
    st.markdown(
        f"""
        <div class="ecoscan-note">
            <strong>Segmentação escolhida:</strong> {html.escape(str(decision.get("selected", pipeline.segmentation_result.name)))}<br>
            {html.escape(str(decision.get("reason", "")))}
        </div>
        """,
        unsafe_allow_html=True,
    )
    candidates = decision.get("candidates") or []
    if candidates:
        st.dataframe(candidates, width="stretch", hide_index=True)
    skipped = decision.get("skipped") or []
    if skipped:
        st.caption("Métodos ignorados por indisponibilidade técnica:")
        st.dataframe(skipped, width="stretch", hide_index=True)


def _render_element_diagnostics(st: Any, pipeline: Any) -> None:
    analysis = pipeline.element_analysis
    metric_cols = st.columns(4)
    metric_cols[0].metric("Elementos", analysis.significant_count)
    metric_cols[1].metric("Área segmentada", _format_percent(analysis.foreground_ratio))
    metric_cols[2].metric("Maior elemento", _format_percent(analysis.largest_area_ratio))
    metric_cols[3].metric("Múltiplos objetos", "sim" if analysis.likely_multi_object else "não")

    st.caption(analysis.warning)
    rows = [
        {
            "id": element.label,
            "bbox": element.bbox_xyxy,
            "centro": element.centroid_xy,
            "área": element.area_pixels,
            "área relativa": element.area_ratio,
            "toca borda": element.touches_border,
        }
        for element in analysis.elements
    ]
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)


