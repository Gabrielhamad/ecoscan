"""Authenticated management pages and model-quality review components.

Role authorization is enforced by the coordinator and server-side services.
"""
from __future__ import annotations

import html
from typing import TYPE_CHECKING, Any

from ecoscan.services.accounts import (
    UserProfile,
    points_ledger_path_from_config,
    read_point_transactions,
    summarize_points_by_user,
)
from ecoscan.disposal.collection_points import CollectionPoint
from ecoscan.services.campaigns import Campaign
from ecoscan.disposal.guidance import DisposalGuidance
from ecoscan.ui.common_views import (
    _class_label,
    _guidance_class_labels,
    _html_list,
    _render_user_error,
)

if TYPE_CHECKING:
    from ecoscan.services.recognition_improvement import RecognitionImprovementPlan


def _render_field_test_form(
    st: Any,
    config: Any,
    active_profile: UserProfile,
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    from ecoscan.services.field_testing import (
        append_field_test_record,
        build_field_test_record,
        field_test_manifest_path_from_config,
        field_test_rows,
        read_field_test_records,
    )

    st.markdown('<div class="ecoscan-section-title">Registrar teste da rodada</div>', unsafe_allow_html=True)
    if active_profile.id.startswith("visitor_"):
        st.info("Entre em uma conta verificada para registrar testes. O reconhecimento continua disponível sem cadastro.")
        return
    st.markdown(
        '<div class="ecoscan-note">Use esta área quando estiver testando com o grupo. '
        "Ela registra se o reconhecimento acertou, errou ou ficou inconclusivo, sem depender de print ou anotação solta.</div>",
        unsafe_allow_html=True,
    )
    class_options = list(config.classes)
    model_options = ["__none__", *class_options]
    with st.form(f"field_test_form_{active_profile.id}"):
        cols = st.columns(2)
        with cols[0]:
            expected_class = st.selectbox(
                "Material testado",
                class_options,
                format_func=lambda class_id: _class_label(class_id, guidance_by_class),
            )
            model_class = st.selectbox(
                "O app indicou",
                model_options,
                format_func=lambda class_id: "Não reconheceu / não anotei"
                if class_id == "__none__"
                else _class_label(class_id, guidance_by_class),
            )
            result_status = st.radio(
                "Resultado",
                ["acertou", "errou", "inconclusivo"],
                horizontal=True,
            )
        with cols[1]:
            device_kind = st.selectbox("Dispositivo", ["celular", "computador", "tablet", "outro"])
            capture_mode = st.selectbox("Entrada usada", ["foto enviada", "câmera ao vivo", "upload no PC"])
            has_confidence = st.checkbox("Informar confiança exibida")
            confidence_percent = st.slider("Confiança (%)", 0, 100, 0, disabled=not has_confidence)
        note = st.text_area(
            "Observação do teste",
            max_chars=600,
            placeholder="ex.: lata Monster virou vidro; garrafa PET com fundo branco acertou",
        )
        submitted = st.form_submit_button("Salvar teste da rodada")

    if submitted:
        try:
            record = build_field_test_record(
                tester_id=active_profile.id,
                tester_name=active_profile.display_name,
                expected_class=expected_class,
                model_class=None if model_class == "__none__" else model_class,
                result_status=result_status,
                device_kind=device_kind,
                capture_mode=capture_mode,
                confidence=(confidence_percent / 100) if has_confidence else None,
                note=note,
            )
            append_field_test_record(field_test_manifest_path_from_config(config), record)
            st.success("Teste registrado. A gestão já consegue usar esse dado na aba Gestão.")
        except Exception as exc:
            _render_user_error(st, exc, context="field_test")

    try:
        recent_tests = read_field_test_records(
            field_test_manifest_path_from_config(config),
            tester_id=active_profile.id,
            limit=8,
        )
    except OSError as exc:
        st.error(str(exc))
        return
    if recent_tests:
        st.dataframe(
            field_test_rows(recent_tests, _guidance_class_labels(guidance_by_class), limit=8),
            width="stretch",
            hide_index=True,
        )


def _render_admin_campaign_operations(
    st: Any,
    campaign: Campaign | None,
    collection_points: list[CollectionPoint],
    point_transactions: list[Any],
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    from ecoscan.services.operations import (
        build_campaign_operations_summary,
        mission_activity_rows,
        published_mission_rows,
    )

    st.markdown('<div class="ecoscan-section-title">Operação da campanha</div>', unsafe_allow_html=True)
    if campaign is None:
        st.info("Campanha ainda não configurada.")
        return

    summary = build_campaign_operations_summary(
        campaign,
        collection_points,
        point_transactions,
        _guidance_class_labels(guidance_by_class),
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Missões publicadas", summary.mission_count)
    metric_cols[1].metric("Pontos possíveis", summary.possible_points)
    metric_cols[2].metric("Participantes pontuados", summary.participant_count)
    metric_cols[3].metric("Pontos recicláveis", summary.recyclable_point_count)

    st.markdown(
        f"""
        <div class="ecoscan-admin-panel">
            <strong>{html.escape(campaign.title)}</strong>
            <p class="ecoscan-muted">{html.escape(campaign.public_message)}</p>
            <span class="ecoscan-card-meta">{html.escape(campaign.owner)} · {html.escape(campaign.weekly_rotation_note)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    city_chips = "".join(
        f'<span class="ecoscan-territory-chip">{html.escape(city)} · {count}</span>'
        for city, count in summary.city_counts
    )
    st.markdown(
        '<div class="ecoscan-ops-grid">'
        '<div class="ecoscan-admin-panel"><strong>Objetivos estratégicos</strong>'
        + _html_list(campaign.strategic_goals)
        + '</div>'
        '<div class="ecoscan-admin-panel"><strong>Rotina da secretaria</strong>'
        + _html_list(campaign.operational_routines)
        + '</div>'
        '<div class="ecoscan-admin-panel"><strong>Públicos atendidos</strong>'
        + _html_list(campaign.audience_segments)
        + f'<div class="ecoscan-territory-chip-row">{city_chips}</div>'
        + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ecoscan-section-title">Desempenho das missões</div>', unsafe_allow_html=True)
    st.dataframe(
        mission_activity_rows(summary),
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="ecoscan-section-title">Missões publicadas ao cidadão</div>', unsafe_allow_html=True)
    st.dataframe(published_mission_rows(summary), width="stretch", hide_index=True)


def _render_admin_recognition_improvement_plan(
    st: Any,
    plan: RecognitionImprovementPlan,
) -> None:
    from ecoscan.services.recognition_improvement import confusion_table_rows, priority_table_rows

    st.markdown('<div class="ecoscan-section-title">Plano de reforço do reconhecimento</div>', unsafe_allow_html=True)
    recommendation_items = "".join(f"<li>{html.escape(item)}</li>" for item in plan.recommendations)
    st.markdown(
        '<div class="ecoscan-admin-panel">'
        "<strong>Próximas ações recomendadas</strong>"
        f"<ul>{recommendation_items}</ul>"
        "</div>",
        unsafe_allow_html=True,
    )

    priority_cards = []
    class_by_priority = {"alta": "high", "média": "medium", "baixa": "low"}
    actionable_priorities = [item for item in plan.priorities if item.score > 0]
    for item in actionable_priorities[:3]:
        reasons = "; ".join(item.reasons[:3])
        priority_cards.append(
            '<div class="ecoscan-priority-card '
            + html.escape(class_by_priority.get(item.priority, "low"))
            + '">'
            f"<span>Prioridade {html.escape(item.priority)} · score {item.score:.1f}</span>"
            f"<strong>{html.escape(item.label)}</strong>"
            f"<p>{html.escape(item.action)}</p>"
            f"<small>{html.escape(reasons)}</small>"
            "</div>"
        )
    if priority_cards:
        st.markdown(
            '<div class="ecoscan-ops-grid">' + "".join(priority_cards) + "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Aguardando histórico e correções para formar prioridade operacional. Faça uma rodada de testes com fotos reais e corrija os erros encontrados.")

    priority_rows = priority_table_rows(plan.priorities)
    if priority_rows:
        st.dataframe(priority_rows, width="stretch", hide_index=True)

    confusion_rows = confusion_table_rows(plan.confusions)
    if confusion_rows:
        st.markdown('<div class="ecoscan-section-title">Confusões críticas para corrigir</div>', unsafe_allow_html=True)
        st.dataframe(confusion_rows, width="stretch", hide_index=True)
    else:
        st.info("Ainda não há confusões registradas por correção. Quando alguém corrigir um erro, ele aparecerá aqui.")


def _render_admin_field_tests(
    st: Any,
    config: Any,
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    from ecoscan.services.field_testing import (
        field_test_class_rows,
        field_test_manifest_path_from_config,
        field_test_rows,
        read_field_test_records,
        summarize_field_tests,
    )

    st.markdown('<div class="ecoscan-section-title">Rodada de testes do grupo</div>', unsafe_allow_html=True)
    records = read_field_test_records(field_test_manifest_path_from_config(config), limit=500)
    labels = _guidance_class_labels(guidance_by_class)
    summary = summarize_field_tests(records)
    cols = st.columns(5)
    cols[0].metric("Testes registrados", summary.total)
    cols[1].metric("Acertos", summary.correct_count)
    cols[2].metric("Erros", summary.wrong_count)
    cols[3].metric("Inconclusivos", summary.inconclusive_count)
    cols[4].metric("No celular", summary.mobile_count)

    if not records:
        st.info("Ainda não há testes da rodada. Peça ao grupo para registrar cada teste na aba Perfil.")
        return

    st.markdown(
        '<div class="ecoscan-admin-table-note">'
        "Use esta leitura junto com as correções do reconhecimento. Classes com muitos erros ou inconclusivos devem virar prioridade de novas fotos."
        "</div>",
        unsafe_allow_html=True,
    )
    by_class = field_test_class_rows(records, labels)
    latest = field_test_rows(records, labels, limit=20)
    cols = st.columns([0.95, 1.05])
    with cols[0]:
        st.markdown('<div class="ecoscan-section-title">Resumo por classe testada</div>', unsafe_allow_html=True)
        st.dataframe(by_class, width="stretch", hide_index=True)
    with cols[1]:
        st.markdown('<div class="ecoscan-section-title">Últimos testes registrados</div>', unsafe_allow_html=True)
        st.dataframe(latest, width="stretch", hide_index=True)


def _render_admin_recognition_quality(
    st: Any,
    config: Any,
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    from ecoscan.services.diagnostics import dataset_status
    from ecoscan.services.field_testing import (
        field_test_manifest_path_from_config,
        read_field_test_records,
    )
    from ecoscan.services.history import history_path_from_config, read_history
    from ecoscan.services.recognition_feedback import (
        feedback_manifest_path_from_config,
        read_recognition_feedback,
    )
    from ecoscan.services.recognition_improvement import build_recognition_improvement_plan
    from ecoscan.services.usage_quality import (
        build_recognition_quality_summary,
        class_quality_rows,
        correction_rows,
    )

    st.markdown('<div class="ecoscan-section-title">Qualidade do reconhecimento</div>', unsafe_allow_html=True)
    history_entries = read_history(history_path_from_config(config), limit=500)
    feedback_entries = read_recognition_feedback(feedback_manifest_path_from_config(config), limit=500)
    field_test_entries = read_field_test_records(field_test_manifest_path_from_config(config), limit=500)
    class_labels = _guidance_class_labels(guidance_by_class)
    summary = build_recognition_quality_summary(history_entries, feedback_entries)
    improvement_plan = build_recognition_improvement_plan(
        history_entries,
        feedback_entries,
        dataset_status(config),
        class_labels,
        field_test_entries=field_test_entries,
        classes=config.classes,
    )

    metric_cols = st.columns(5)
    metric_cols[0].metric("Análises salvas", summary.analysis_count)
    metric_cols[1].metric("Aceitas", summary.accepted_count)
    metric_cols[2].metric("Inconclusivas", summary.uncertain_count)
    metric_cols[3].metric("Baixa confiança", summary.low_confidence_count)
    metric_cols[4].metric("Correções", summary.feedback_count)
    if summary.average_confidence is not None:
        st.caption(f"Confiança média registrada: {summary.average_confidence:.1%}.")

    st.markdown(
        '<div class="ecoscan-admin-table-note">'
        "Use estes dados para decidir quais fotos coletar primeiro. Classes com baixa confiança ou correções frequentes "
        "devem receber mais imagens reais, em vários ângulos e ambientes."
        "</div>",
        unsafe_allow_html=True,
    )
    _render_admin_recognition_improvement_plan(st, improvement_plan)

    correction_table = correction_rows(feedback_entries, class_labels)
    class_table = class_quality_rows(history_entries, class_labels)
    cols = st.columns([1, 1])
    with cols[0]:
        st.markdown('<div class="ecoscan-section-title">Correções enviadas</div>', unsafe_allow_html=True)
        if correction_table:
            st.dataframe(correction_table, width="stretch", hide_index=True)
        else:
            st.info("Ainda não há correções registradas. Peça ao grupo para corrigir cada erro de reconhecimento.")
    with cols[1]:
        st.markdown('<div class="ecoscan-section-title">Classes para reforçar</div>', unsafe_allow_html=True)
        if class_table:
            st.dataframe(class_table, width="stretch", hide_index=True)
        else:
            st.info("Ative salvar histórico ou valide imagens para formar indicadores por classe.")


def _render_admin_tab(
    st: Any,
    config: Any,
    active_profile: UserProfile,
    profiles: tuple[UserProfile, ...],
    campaign: Campaign | None,
    collection_points: list[CollectionPoint],
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    from ecoscan.ui.learning import render_review
    st.markdown('<div class="ecoscan-section-title">Gestão ambiental</div>', unsafe_allow_html=True)
    if not active_profile.is_admin:
        st.warning("Este painel é restrito ao perfil administrativo.")
        return

    render_review(st, config, active_profile)

    ledger_path = points_ledger_path_from_config(config)
    point_transactions = read_point_transactions(ledger_path, limit=500)

    cols = st.columns(3)
    cols[0].metric("Perfis locais de demonstração", len(profiles))
    cols[1].metric("Missões", len(campaign.missions) if campaign else 0)
    cols[2].metric("Pontos de coleta", len(collection_points))

    with st.expander("Cadastros reais e confirmação de e-mail",
                     key="real_users_panel", on_change="rerun") as directory_panel:
        if directory_panel.open:
            st.button("Atualizar cadastros", key="refresh_real_users")
            try:
                from ecoscan.services.participant_directory import registered_users
                real_users = registered_users(st.session_state.get("auth_access_token"),
                                              dict(st.secrets.get("access", {})))
                st.caption(f"{len(real_users)} conta(s) consultada(s), limite de 1.000. Cadastro não significa contribuição enviada.")
                st.dataframe(real_users, hide_index=True, width="stretch")
            except (ValueError, PermissionError, OSError) as exc:
                st.warning(str(exc))

    _render_admin_campaign_operations(
        st,
        campaign,
        collection_points,
        point_transactions,
        guidance_by_class,
    )
    from ecoscan.ui.community import render_campaign_editor, render_reports
    render_campaign_editor(st, config)

    _render_admin_recognition_quality(st, config, guidance_by_class)
    _render_admin_field_tests(st, config, guidance_by_class)

    st.markdown('<div class="ecoscan-section-title">Ranking e participação</div>', unsafe_allow_html=True)
    point_rows = summarize_points_by_user(ledger_path, profiles)
    if point_rows:
        st.dataframe(point_rows, width="stretch", hide_index=True)
    else:
        st.info("Ainda não há pontuação registrada.")

    render_reports(st, admin=True, key="admin_civic_reports")


