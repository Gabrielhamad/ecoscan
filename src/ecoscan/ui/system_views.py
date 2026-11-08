"""Technical, administrative diagnostics and readiness views.

Only the application coordinator decides which authenticated audience can access
these views. Domain services are imported on demand inside render functions.
"""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from ecoscan.disposal.guidance import DisposalGuidance
from ecoscan.ui.common_views import (
    _badge,
    _guidance_class_labels,
    _html_list,
    _public_code,
    _public_ui_text,
    _render_user_error,
    _status_item,
)


def _render_overview_strip(st: Any, config: Any) -> None:
    from ecoscan.services.aps_audit import build_aps_audit, summarize_audit
    from ecoscan.services.dataset_governance import build_dataset_readiness
    from ecoscan.services.diagnostics import dataset_status, model_status

    selected_model = model_status(config)
    dataset = dataset_status(config)
    audit_summary = summarize_audit(build_aps_audit(config))
    readiness = build_dataset_readiness(config, target_per_class=50)[0]

    raw_total = sum(dataset.raw_counts.values())
    curated_total = sum(dataset.curated_counts.values())
    model_tone = "ok" if selected_model.selected_kind == "semantic_onnx_assisted" else "warn"
    model_labels = {"semantic_onnx_assisted": "reconhecimento assistido ONNX"}
    model_label = model_labels.get(selected_model.selected_kind, "sem modelo")
    dataset_tone = "ok" if readiness.ready_for_final_training else "warn"
    strip = "".join(
        [
            _status_item(
                "Modelo ativo",
                model_label,
                "release atual carregada" if selected_model.selected_kind == "semantic_onnx_assisted" else "modelo indisponível",
                model_tone,
            ),
            _status_item(
                "Prontidão técnica",
                f"{audit_summary['readiness_score']}%",
                "qualidade do sistema",
                "ok" if float(audit_summary["readiness_score"]) >= 70 else "warn",
            ),
            _status_item(
                "Base de imagens",
                f"{raw_total} brutas / {curated_total} curadas",
                f"faltam {readiness.missing_raw_total} fotos brutas",
                dataset_tone,
            ),
            _status_item(
                "Validação",
                "executável",
                "validação automatizada disponível",
                "ok",
            ),
        ]
    )
    st.markdown(f'<section class="ecoscan-status-strip">{strip}</section>', unsafe_allow_html=True)


def _render_model_status(st: Any, config: Any) -> None:
    from ecoscan.image_processing.contracts import model_processing_compatible, processing_contract
    from ecoscan.services.diagnostics import model_status

    status = model_status(config)
    if status.selected_path and not model_processing_compatible(Path(status.selected_path), processing_contract(config)):
        st.markdown(_badge("Modelo aguarda novo treinamento", "warn"), unsafe_allow_html=True)
        st.caption("Preparação atualizada. Hipóteses não são confirmadas até treinar e validar um modelo compatível.")
    elif status.selected_kind == "semantic_onnx_assisted":
        st.markdown(_badge("Reconhecimento assistido ONNX ativo", "ok"), unsafe_allow_html=True)
    else:
        st.markdown(_badge("Nenhum modelo disponível", "danger"), unsafe_allow_html=True)
    if status.selected_path:
        st.caption(status.selected_path)


def _dataset_rows(st: Any, config: Any, guidance_by_class: dict[str, DisposalGuidance]) -> tuple[list[dict], Any]:
    from ecoscan.services.diagnostics import dataset_status

    status = dataset_status(config)
    rows = []
    for class_id in config.classes:
        guidance = guidance_by_class.get(class_id)
        rows.append(
            {
                "classe": class_id,
                "nome": guidance.display_name if guidance else class_id,
                "categoria": guidance.environmental_category if guidance else "",
                "brutas": status.raw_counts[class_id],
                "curadas": status.curated_counts[class_id],
                "treino": status.train_counts[class_id],
                "validação": status.validation_counts[class_id],
                "teste": status.test_counts[class_id],
            }
        )
    return rows, status


def _render_dataset_status(st: Any, config: Any, guidance_by_class: dict[str, DisposalGuidance]) -> None:
    rows, status = _dataset_rows(st, config, guidance_by_class)
    raw_total = sum(status.raw_counts.values())
    curated_total = sum(status.curated_counts.values())
    split_total = sum(status.train_counts.values()) + sum(status.validation_counts.values()) + sum(status.test_counts.values())
    special_total = 0
    for class_id in config.classes:
        guidance = guidance_by_class.get(class_id)
        category = guidance.environmental_category.lower() if guidance else ""
        if "especial" in category or "eletro" in category or "perigoso" in category:
            special_total += status.raw_counts[class_id]

    metric_cols = st.columns(4)
    metric_cols[0].metric("Imagens brutas", raw_total)
    metric_cols[1].metric("Curadas", curated_total)
    metric_cols[2].metric("Em treino/val/teste", split_total)
    metric_cols[3].metric("Resíduos especiais", special_total)
    st.dataframe(rows, width="stretch", hide_index=True)


def _render_dataset_readiness(st: Any, config: Any) -> None:
    from ecoscan.services.dataset_governance import build_dataset_readiness

    summary, rows = build_dataset_readiness(config, target_per_class=50)
    ready_label = "sim" if summary.ready_for_final_training else "não"
    metric_cols = st.columns(4)
    metric_cols[0].metric("Alvo por classe", summary.target_per_class)
    metric_cols[1].metric("Classes no alvo bruto", f"{summary.classes_at_raw_target}/{summary.class_count}")
    metric_cols[2].metric("Faltam fotos brutas", summary.missing_raw_total)
    metric_cols[3].metric("Pronto p/ treino final", ready_label)

    planning_rows = [
        {
            "classe": row.class_id,
            "nome": row.display_name,
            "categoria": row.environmental_category,
            "fotos brutas": row.raw_count,
            "fotos curadas": row.curated_count,
            "faltam brutas": row.missing_raw,
            "faltam curadas": row.missing_curated,
            "gate": row.gate,
            "próxima ação": row.next_action,
        }
        for row in rows
    ]
    st.dataframe(planning_rows, width="stretch", hide_index=True)


def _render_ingestion_results(st: Any, results: list[dict[str, Any]]) -> None:
    if not results:
        return
    summary = {
        "saved": sum(1 for result in results if result["status"] == "saved"),
        "duplicate": sum(1 for result in results if result["status"] == "duplicate"),
        "rejected": sum(1 for result in results if result["status"] == "rejected"),
    }
    st.markdown(
        "".join(
            [
                _badge(f"{summary['saved']} salvas", "ok"),
                _badge(f"{summary['duplicate']} duplicadas", "warn"),
                _badge(f"{summary['rejected']} rejeitadas", "danger" if summary["rejected"] else "ok"),
            ]
        ),
        unsafe_allow_html=True,
    )
    rows = [
        {
            "status": result["status"],
            "arquivo": result["original_name"],
            "classe": result["class_id"],
            "destino": result["saved_path"] or result["duplicate_of"],
            "mensagem": result["message"],
            "tamanho": f"{result['width']}x{result['height']}" if result["width"] and result["height"] else "",
        }
        for result in results
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def _render_dependencies(st: Any) -> None:
    from ecoscan.services.diagnostics import dependency_status

    rows = [
        {
            "dependência": item.name,
            "status": "ok" if item.installed else "ausente",
            "uso": item.purpose,
        }
        for item in dependency_status()
    ]
    st.dataframe(rows, width="stretch")


def _render_access_testing_panel(st: Any) -> None:
    from ecoscan.services.access_plan import (
        access_link_rows,
        build_access_plan,
        probe_access_services,
        shareable_access_text,
    )

    plan = build_access_plan()
    services = probe_access_services(timeout_seconds=1.2)
    status_html = "".join(
        _status_item(
            service.label,
            "OK" if service.ok else "não respondeu",
            service.note,
            "ok" if service.ok else "warn",
        )
        for service in services
    )
    st.markdown(f'<section class="ecoscan-status-strip">{status_html}</section>', unsafe_allow_html=True)

    st.markdown(
        '<div class="ecoscan-note">Use estes links para uma rodada controlada com colegas. '
        "Em celular, todos precisam estar na mesma rede Wi-Fi; fora da rede local, publique em HTTPS.</div>",
        unsafe_allow_html=True,
    )

    local_cols = st.columns(3)
    for column, link in zip(local_cols, plan.local_links):
        column.link_button(link.label, link.url, width="stretch")

    network_cols = st.columns(3)
    for column, link in zip(network_cols, plan.network_links):
        column.link_button(link.label, link.url, width="stretch")

    st.markdown('<div class="ecoscan-section-title">Mensagem para enviar ao grupo</div>', unsafe_allow_html=True)
    st.code(shareable_access_text(plan), language="text")

    st.markdown(
        '<div class="ecoscan-ops-grid">'
        '<div class="ecoscan-admin-panel"><strong>Regras de acesso</strong>'
        + _html_list(plan.notes)
        + '</div>'
        '<div class="ecoscan-admin-panel"><strong>Roteiro de teste</strong>'
        + _html_list(plan.test_steps)
        + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.dataframe(access_link_rows(plan), width="stretch", hide_index=True)


def _render_error_catalog(st: Any) -> None:
    from ecoscan.errors import error_catalog
    rows = [
        {
            "código": item.code,
            "categoria": _public_ui_text(item.category),
            "título": _public_ui_text(item.title),
            "mensagem": _public_ui_text(item.message),
            "ação recomendada": _public_ui_text(item.action),
        }
        for item in error_catalog()
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def _render_free_hosting_panel(st: Any, config: Any) -> None:
    from ecoscan.services.deployment_readiness import build_free_hosting_plan, deployment_check_rows

    plan = build_free_hosting_plan(config)
    st.markdown(
        f"""
        <div class="ecoscan-admin-panel">
            <strong>{html.escape(plan.recommended_platform)}</strong>
            <p>{html.escape(plan.summary)}</p>
            <p><strong>Entrada:</strong> {html.escape(plan.entrypoint)} · <strong>URL esperada:</strong> {html.escape(plan.expected_url)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    cols[0].metric("Foto/câmera no app", "sim" if plan.can_use_camera_photo else "não")
    cols[1].metric("Recicla SP Live grátis", "sim" if plan.live_mode_available else "não")
    cols[2].metric("Checklist", sum(1 for item in plan.checks if item.status == "ok"), f"{len(plan.checks)} itens")

    step_items = "".join(f"<li>{html.escape(step)}</li>" for step in plan.steps)
    limitation_items = "".join(f"<li>{html.escape(item)}</li>" for item in plan.limitations)
    st.markdown(
        '<div class="ecoscan-ops-grid">'
        '<div class="ecoscan-admin-panel"><strong>Passo a passo para publicar</strong>'
        f"<ol>{step_items}</ol>"
        "</div>"
        '<div class="ecoscan-admin-panel"><strong>Limitações do gratuito</strong>'
        f"<ul>{limitation_items}</ul>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.dataframe(deployment_check_rows(plan.checks), width="stretch", hide_index=True)


def _completion_label(status: str) -> str:
    labels = {
        "ok": "pronto",
        "attention": "atenção",
        "pending": "pendente",
        "failed": "falha",
    }
    return labels.get(status, status)


def _render_completion_panel(st: Any, config: Any) -> None:
    from ecoscan.services.completion import build_completion_plan

    plan = build_completion_plan(config)
    status_title = (
        "Pronto para demonstração controlada"
        if plan.ready_for_demo
        else "Ainda exige ajuste antes da apresentação"
    )
    status_detail = (
        "O fluxo principal, a experiência de usuário, a gestão, a câmera e as evidências técnicas estão em condição de apresentação."
        if plan.ready_for_demo
        else "Revise os itens em atenção e pendentes antes de tratar o sistema como entrega final."
    )
    st.markdown(
        f"""
        <div class="ecoscan-completion-banner">
            <strong>{html.escape(status_title)}</strong>
            <span>{html.escape(status_detail)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Score técnico", f"{plan.readiness_score}%")
    metric_cols[1].metric("Aceite", f"{plan.acceptance_ok} OK", f"{plan.acceptance_failed} falha")
    metric_cols[2].metric("Base bruta", plan.raw_total, f"faltam {plan.missing_raw_total}")
    metric_cols[3].metric("Base curada", plan.curated_total, f"faltam {plan.missing_curated_total}")

    cards = []
    for action in plan.actions:
        cards.append(
            '<div class="ecoscan-completion-card {status}">'
            "<span>{area} · {label}</span>"
            "<strong>{title}</strong>"
            "<p>{detail}</p>"
            "<small>Próximo passo: {next_step}</small>"
            "</div>".format(
                status=html.escape(action.status),
                area=html.escape(action.area),
                label=html.escape(_completion_label(action.status)),
                title=html.escape(action.title),
                detail=html.escape(action.detail),
                next_step=html.escape(action.next_step),
            )
        )
    st.markdown('<div class="ecoscan-completion-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)

    if plan.final_model_exists:
        st.success("Modelo final encontrado. A próxima etapa é comparar métricas e validar em imagens reais.")
    else:
        st.warning(
            "Conclusão honesta: o produto está pronto para demonstração e uso orientativo, "
            "mas o reconhecimento definitivo ainda depende de base curada e treino do modelo final."
        )

    st.markdown('<div class="ecoscan-section-title">Comandos finais recomendados</div>', unsafe_allow_html=True)
    st.code(
        "\n".join(
            [
                "python scripts\\run_acceptance_checks.py",
                "python scripts\\generate_final_readiness.py",
                "python scripts\\generate_academic_report.py",
                "python scripts\\prepare_delivery_pack.py legacy-report",
            ]
        ),
        language="powershell",
    )
    _render_final_readiness(st, config)


def _render_final_readiness(st: Any, config: Any) -> None:
    from ecoscan.services.final_readiness import (
        build_final_readiness_items,
        summarize_final_readiness,
    )

    items = build_final_readiness_items(config)
    summary = summarize_final_readiness(items)
    st.markdown('<div class="ecoscan-section-title">Estrutura preparada para a fase final</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    cols[0].metric("Pronto", summary.get("ready", 0))
    cols[1].metric("Preparado", summary.get("prepared", 0))
    cols[2].metric("Depende de dados/treino", summary.get("needs_data", 0) + summary.get("needs_training", 0))
    cols[3].metric("Evolução futura", summary.get("future", 0))
    st.dataframe(
        [
            {
                "área": item.area,
                "item": item.title,
                "status": item.status,
                "preparado_para_depois": "sim" if item.prepared_for_later else "parcial",
                "evidência": item.evidence,
                "próximo_passo": item.next_step,
            }
            for item in items
        ],
        width="stretch",
        hide_index=True,
    )


def _model_governance_status_label(status: str) -> str:
    labels = {
        "ready": "apto",
        "prepared": "preparado",
        "attention": "atenção",
        "blocked": "bloqueado",
    }
    return labels.get(status, status)


def _render_model_governance(
    st: Any,
    config: Any,
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    from ecoscan.services.field_testing import (
        field_test_manifest_path_from_config,
        read_field_test_records,
    )
    from ecoscan.services.model_governance import (
        build_model_governance_plan,
        hard_case_table_rows,
        metric_snapshot_rows,
        model_gate_table_rows,
    )
    from ecoscan.services.recognition_feedback import (
        feedback_manifest_path_from_config,
        read_recognition_feedback,
    )

    labels = _guidance_class_labels(guidance_by_class)
    feedback_entries = read_recognition_feedback(feedback_manifest_path_from_config(config), limit=500)
    field_test_entries = read_field_test_records(field_test_manifest_path_from_config(config), limit=500)
    plan = build_model_governance_plan(
        config,
        feedback_entries=feedback_entries,
        field_test_entries=field_test_entries,
        class_labels=labels,
    )
    status_label = _model_governance_status_label(plan.promotion_status)

    st.markdown('<div class="ecoscan-section-title">Governança do modelo final</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="ecoscan-completion-banner">
            <strong>Promoção do reconhecimento: {html.escape(status_label)}</strong>
            <span>{html.escape(plan.promotion_label)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    cols[0].metric("Modelo ativo", _public_ui_text(plan.active_model_kind))
    cols[1].metric("Relatórios", plan.evaluation_count)
    cols[2].metric("Casos difíceis", len(plan.hard_cases))
    cols[3].metric("Status", status_label)

    recommendation_items = "".join(f"<li>{html.escape(item)}</li>" for item in plan.recommendations)
    st.markdown(
        '<div class="ecoscan-admin-panel">'
        "<strong>Regra de engenharia</strong>"
        f"<ul>{recommendation_items}</ul>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.dataframe(model_gate_table_rows(plan.gates), width="stretch", hide_index=True)

    metric_rows = metric_snapshot_rows(plan)
    if metric_rows:
        st.markdown('<div class="ecoscan-section-title">Métricas comparativas</div>', unsafe_allow_html=True)
        st.dataframe(metric_rows, width="stretch", hide_index=True)
    else:
        st.info("Ainda não há relatório de avaliação suficiente para comparar modelos.")

    case_rows = hard_case_table_rows(plan.hard_cases, labels)
    if case_rows:
        st.markdown('<div class="ecoscan-section-title">Casos difíceis para regressão</div>', unsafe_allow_html=True)
        st.dataframe(case_rows, width="stretch", hide_index=True)
    else:
        st.info("Quando o grupo registrar erros reais, eles aparecerão aqui como validação obrigatória do próximo modelo.")


def _render_delivery_pack(st: Any, config: Any) -> None:
    from ecoscan.services.delivery_pack import build_delivery_pack, write_delivery_pack

    pack = build_delivery_pack(config)
    selected_model = _public_ui_text(pack.selected_model)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Prontidão", f"{pack.readiness_score}%")
    metric_cols[1].metric("Imagens brutas", pack.raw_total)
    metric_cols[2].metric("Imagens curadas", pack.curated_total)
    metric_cols[3].metric("Modelo ativo", selected_model)

    if st.button("Gerar pacote técnico"):
        try:
            paths = write_delivery_pack(config)
            st.success(f"Pacote gerado em {paths['index'].parent}")
        except Exception as exc:
            _render_user_error(st, exc, context="delivery_pack")

    rows = [
        {
            "código": criterion.code,
            "cenário": _public_ui_text(criterion.scenario),
            "status": criterion.status,
            "evidência": criterion.evidence,
            "nota": _public_ui_text(criterion.note),
        }
        for criterion in pack.acceptance
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def _render_acceptance_checks(st: Any, config: Any) -> None:
    if st.button("Rodar validação do sistema"):
        try:
            from ecoscan.services.acceptance_checks import run_acceptance_checks
            report = run_acceptance_checks(config)
            st.session_state["acceptance_checks_report"] = report
            summary = report.summary
            st.success(
                "Validação concluída: "
                f"{summary.get('ok', 0)} ok, "
                f"{summary.get('attention', 0)} atenção, "
                f"{summary.get('pending', 0)} pendente, "
                f"{summary.get('failed', 0)} falha."
            )
        except Exception as exc:
            _render_user_error(st, exc, context="acceptance_checks")

    report = st.session_state.get("acceptance_checks_report")
    if report is None:
        return
    rows = [
        {
            "código": check.code,
            "área": _public_ui_text(check.area),
            "status": check.status,
            "evidência": check.evidence,
            "detalhes": _public_ui_text(check.details),
        }
        for check in report.checks
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def _render_aps_audit(st: Any, config: Any) -> None:
    from ecoscan.services.aps_audit import build_aps_audit, summarize_audit

    items = build_aps_audit(config)
    summary = summarize_audit(items)
    counts = summary["counts"]

    metric_cols = st.columns(4)
    metric_cols[0].metric("Prontidão técnica", f"{summary['readiness_score']}%")
    metric_cols[1].metric("OK", counts.get("ok", 0))
    metric_cols[2].metric("Atenção", counts.get("attention", 0))
    metric_cols[3].metric("Pendente", counts.get("pending", 0))

    rows = [
        {
            "código": _public_code(item.code),
            "área": _public_ui_text(item.area),
            "prioridade": item.priority,
            "status": item.status,
            "critério": _public_ui_text(item.requirement),
            "próxima ação": _public_ui_text(item.next_action),
        }
        for item in items
    ]
    st.dataframe(rows, width="stretch", hide_index=True)

    attention = [
        {
            "código": _public_code(item.code),
            "ponto": _public_ui_text(item.rationale),
            "próxima ação": _public_ui_text(item.next_action),
        }
        for item in items
        if item.priority == "alta" and item.status in {"attention", "pending"}
    ]
    if attention:
        st.markdown(
            '<div class="ecoscan-note">Os itens abaixo são os que mais influenciam a qualidade final: '
            "base de imagens real, curadoria e modelo final.</div>",
            unsafe_allow_html=True,
        )
        st.dataframe(attention, width="stretch", hide_index=True)


def _render_history(st: Any, config: Any) -> None:
    from ecoscan.services.history import history_path_from_config, read_history

    entries = read_history(history_path_from_config(config), limit=30)
    if not entries:
        st.write("Nenhum registro salvo.")
        return
    rows = [
        {
            "data_utc": entry.timestamp_utc,
            "classe": entry.predicted_class or "__uncertain__",
            "confiança": entry.probability,
            "modelo": entry.model_type,
            "filtro": entry.filter_name,
            "sequência de filtro": entry.filter_decision or entry.filter_name,
            "segmentação": entry.segmentation_decision or entry.segmentation_name,
            "qualidade": (
                f"{entry.capture_quality_status} ({entry.capture_quality_score}/100)"
                if entry.capture_quality_status and entry.capture_quality_score is not None
                else entry.capture_quality_status
            ),
            "elementos": entry.elements_count,
            "categoria": entry.environmental_category,
        }
        for entry in reversed(entries)
    ]
    st.dataframe(rows, width="stretch")


