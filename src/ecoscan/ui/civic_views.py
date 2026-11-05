"""Citizen reports and their UI rendering, isolated from the app coordinator."""
from __future__ import annotations

import html
from typing import Any

from ecoscan.app.processing_options import ProcessingPipelineOptions
from ecoscan.services.accounts import UserProfile
from ecoscan.ui.common_views import _render_user_error
from ecoscan.ui.interaction_helpers import _temporary_upload
from ecoscan.ui.processing_views import _render_photo_processing_summary


def _render_civic_report_status(st: Any, record: Any) -> None:
    tone = ""
    if record.verification_status == "triagem_inconclusiva":
        tone = "inconclusivo"
    elif record.verification_status == "imagem_insuficiente":
        tone = "insuficiente"
    st.markdown(
        f"""
        <div class="ecoscan-report-status {tone}">
            <strong>{html.escape(record.verification_status.replace("_", " ").title())}</strong>
            <span>{html.escape(record.verifier_note)}</span>
            <span class="ecoscan-card-meta">Classe provável: {html.escape(str(record.detected_class or record.top_class or "não identificada"))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_civic_reports_tab(
    st: Any,
    config: Any,
    active_profile: UserProfile,
    pipeline_options: ProcessingPipelineOptions,
) -> None:
    st.markdown('<div class="ecoscan-section-title">Denunciar mau descarte</div>', unsafe_allow_html=True)
    if active_profile.id.startswith("visitor_"):
        st.info("Entre em uma conta verificada para enviar um relato à secretaria. Visitantes podem consultar o mapa e as orientações de descarte.")
        return
    from uuid import uuid4

    from ecoscan.services.community_store import community_enabled, community_store
    from ecoscan.ui.community import credentials, render_reports

    if not community_enabled():
        st.info("O recebimento compartilhado está em preparação. Nenhum relato novo será salvo em arquivos temporários.")
        return
    st.session_state.setdefault("civic_submission_id", str(uuid4()))
    st.markdown(
        '<div class="ecoscan-note">A denúncia usa o mesmo tratamento de imagem, segmentação e reconhecimento '
        "para fazer triagem técnica da evidência. O resultado indica consistência visual, não substitui vistoria oficial.</div>",
        unsafe_allow_html=True,
    )

    form_col, info_col = st.columns([1.05, 0.95])
    with form_col:
        report_source = st.radio("Evidência", ["Câmera", "Imagem"], horizontal=True, key="civic_report_source")
        if report_source == "Câmera":
            report_file = st.camera_input("Fotografar descarte irregular", key="civic_report_camera")
            source_kind = "camera"
        else:
            report_file = st.file_uploader(
                "Enviar foto da denúncia",
                type=["jpg", "jpeg", "png"],
                key="civic_report_upload",
            )
            source_kind = "upload"
        location_note = st.text_input("Local aproximado", placeholder="ex.: rua, bairro, ponto de referência", max_chars=300)
        description = st.text_area("Descrição breve", placeholder="ex.: resíduos descartados perto de área verde", max_chars=2000)
        contact = ""  # Responses are delivered through the authenticated profile.
        consent = st.checkbox("Autorizo enviar esta foto e o relato para análise da equipe. Evitarei rostos, placas e dados de terceiros.")
        st.caption("Projeto educativo: não substitui os canais oficiais de atendimento da Prefeitura.")
        if st.button("Iniciar outro relato", key="civic_new_submission"):
            st.session_state["civic_submission_id"] = str(uuid4())
            st.session_state.pop("last_civic_report_record", None)
            st.session_state.pop("last_civic_report_result", None)

        if report_file is None:
            st.caption("Adicione uma foto da situação para liberar o registro da denúncia.")
        if st.button("Analisar e registrar denúncia", disabled=report_file is None or not consent or not location_note.strip() or not description.strip()):
            temp_path = _temporary_upload(report_file, prefix="report")
            try:
                with st.spinner("Processando evidência da denúncia..."):
                    from ecoscan.services.analysis_service import analyze_waste_image
                    report_result = analyze_waste_image(temp_path, config, options=pipeline_options)
                from ecoscan.services.civic_reports import build_civic_report_record
                record = build_civic_report_record(
                    report_result,
                    evidence_path=temp_path,
                    location_note=location_note,
                    description=description,
                    contact=contact,
                    source_kind=source_kind,
                    submitted_by=active_profile.id,
                )
                from ecoscan.services.civic_reports import CivicReportRecord
                saved = community_store().submit(record, report_file.getvalue(),
                    submission_id=st.session_state["civic_submission_id"],
                    consent=consent, **credentials(st))
                st.session_state["last_civic_report_record"] = CivicReportRecord(**saved["record"])
                st.session_state["last_civic_report_result"] = report_result
                st.success("Relato confirmado no banco e disponível para a equipe. Protocolo: " + saved["id"])
            except Exception as exc:
                _render_user_error(st, exc, context="civic_report")
            finally:
                temp_path.unlink(missing_ok=True)
    with info_col:
        st.markdown(
            """
            <div class="ecoscan-admin-panel">
                <strong>Como a triagem funciona</strong>
                <ul>
                    <li>valida se a imagem é legível;</li>
                    <li>aplica filtragem e segmentação adaptativas;</li>
                    <li>estima o resíduo mais provável;</li>
                    <li>registra qualidade, confiança e elementos detectados;</li>
                    <li>mantém a evidência para revisão da gestão ambiental.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Foto privada no banco compartilhado. A resposta poderá ser acompanhada no Perfil.")

    record = st.session_state.get("last_civic_report_record")
    report_result = st.session_state.get("last_civic_report_result")
    if record is not None:
        _render_civic_report_status(st, record)
    if report_result is not None:
        _render_photo_processing_summary(st, report_result.pipeline)

    render_reports(st, key="civic_history")


