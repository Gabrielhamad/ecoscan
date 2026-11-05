from __future__ import annotations

import base64
import hashlib
import html
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ecoscan.app.processing_options import ProcessingPipelineOptions
from ecoscan.config import load_config
from ecoscan.disposal.collection_points import (
    CollectionPoint,
    build_collection_point_directions_url,
    build_collection_point_map_url,
    filter_collection_points,
    rank_collection_points,
)
from ecoscan.disposal.guidance import DisposalGuidance
from ecoscan.disposal.impact import (
    EnvironmentalImpact,
    get_environmental_impact,
)
from ecoscan.disposal.targets import (
    DisposalTarget,
    build_map_search_url,
    get_disposal_target,
)
from ecoscan.services.accounts import (
    UserProfile,
    points_ledger_path_from_config,
    read_point_transactions,
    summarize_points_by_user,
    total_points_for_user,
)
from ecoscan.services.campaigns import (
    Campaign,
    Mission,
    campaign_path_from_config,
    evaluate_mission_submission,
    load_campaign,
)
from ecoscan.services.photo_requirements import PhotoRequirement
from ecoscan.services.recognition_safety import (
    RecognitionSafetyDecision,
    build_recognition_safety_decision,
    capture_photo_tips,
)
from ecoscan.ui.app_resources import load_app_resources
from ecoscan.ui.education import render_education
from ecoscan.ui.identity import render_identity
from ecoscan.ui.navigation import navigation_for
from ecoscan.ui.processing_controls import (
    FILTERS,
    SEGMENTATIONS,
    select_filter_parameters,
    select_segmentation_parameters,
)
from ecoscan.ui.scope import render_scope
from ecoscan.ui.processing_views import (
    _format_percent as _format_percent,
    _render_quality_snapshot as _render_quality_snapshot,
    _render_capture_quality_advice as _render_capture_quality_advice,
    _render_photo_processing_summary as _render_photo_processing_summary,
    _method_chip as _method_chip,
    _render_processing_evidence as _render_processing_evidence,
    _render_pipeline_diagnostics as _render_pipeline_diagnostics,
    _render_filter_decision as _render_filter_decision,
    _render_segmentation_decision as _render_segmentation_decision,
    _render_element_diagnostics as _render_element_diagnostics,
)
from ecoscan.ui.disposal_views import (
    _render_environmental_impact as _render_environmental_impact,
    _format_point_materials as _format_point_materials,
    _render_collection_point_cards as _render_collection_point_cards,
    _render_photo_requirement_plan as _render_photo_requirement_plan,
    _render_disposal_action_panel as _render_disposal_action_panel,
    _render_recognition_decision as _render_recognition_decision,
    _render_public_next_action as _render_public_next_action,
)
from ecoscan.utils.logging_config import configure_logging

if TYPE_CHECKING:
    from ecoscan.services.public_flow import PublicNextAction
    from ecoscan.services.recognition_improvement import RecognitionImprovementPlan


LOGGER = logging.getLogger(__name__)


def _format_count(value: int, singular: str, plural: str | None = None) -> str:
    label = singular if value == 1 else (plural or f"{singular}s")
    return f"{value} {label}"


def _render_theme(st: Any) -> None:
    from ecoscan.ui.appearance import render_theme
    render_theme(st)


def _render_public_app_chrome(st: Any) -> None:
    st.markdown('<style>[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display:none}</style>', unsafe_allow_html=True)


def _badge(label: str, tone: str = "ok") -> str:
    return f'<span class="ecoscan-badge ecoscan-badge-{tone}">{html.escape(label)}</span>'


def _load_campaign_config(config: Any) -> Campaign | None:
    from ecoscan.services.campaigns import campaign_from_payload
    from ecoscan.services.community_store import community_enabled, community_store

    try:
        if community_enabled():
            snapshot = community_store().campaign()
            if snapshot:
                return campaign_from_payload(snapshot["record"])
            import streamlit as st
            st.caption("Campanha de referência do Recicla SP. A primeira publicação da equipe ainda está pendente.")
            return load_campaign(campaign_path_from_config(config))
        return load_campaign(campaign_path_from_config(config))
    except Exception as exc:
        LOGGER.warning("campaign_load_failed detail=%s", exc)
        import streamlit as st
        st.warning("Campanha indisponível no momento. A análise de fotos e as orientações continuam disponíveis.")
        return None


def _target_for_guidance(
    guidance: DisposalGuidance | None,
    targets_by_class: dict[str, DisposalTarget],
) -> DisposalTarget | None:
    if guidance is None:
        return None
    try:
        return get_disposal_target(guidance.class_id, targets_by_class)
    except Exception as exc:
        LOGGER.warning("disposal_target_missing class_id=%s detail=%s", guidance.class_id, exc)
        return None


def _impact_for_guidance(
    guidance: DisposalGuidance | None,
    impacts_by_class: dict[str, EnvironmentalImpact],
) -> EnvironmentalImpact | None:
    if guidance is None:
        return None
    try:
        return get_environmental_impact(guidance.class_id, impacts_by_class)
    except Exception as exc:
        LOGGER.warning("environmental_impact_missing class_id=%s detail=%s", guidance.class_id, exc)
        return None


def _render_user_error(st: Any, exc: BaseException, *, context: str) -> None:
    from ecoscan.errors import describe_exception
    error = describe_exception(exc)
    log_message = (
        "ui_handled_error context=%s code=%s category=%s detail=%s"
        % (context, error.code, error.category, error.technical_detail)
    )
    if error.code == "APP-001":
        LOGGER.exception(log_message)
    else:
        LOGGER.warning(log_message)

    st.error(f"{error.code} - {error.title}: {error.message}")
    st.info(f"Ação recomendada: {error.action}")
    if error.technical_detail:
        with st.expander("Detalhe técnico"):
            st.code(error.technical_detail)


def _class_label(class_id: str, guidance_by_class: dict[str, DisposalGuidance]) -> str:
    guidance = guidance_by_class.get(class_id)
    if not guidance:
        return class_id
    return f"{guidance.display_name} ({class_id})"


def _class_chip(class_id: str, guidance_by_class: dict[str, DisposalGuidance]) -> str:
    guidance = guidance_by_class.get(class_id)
    label = guidance.display_name if guidance else class_id
    category = guidance.environmental_category if guidance else "classe ativa"
    return (
        '<span class="ecoscan-chip">'
        f"{html.escape(label)} <small>{html.escape(category)}</small>"
        "</span>"
    )


def _status_item(label: str, value: str, detail: str, tone: str = "ok") -> str:
    tone = tone if tone in {"ok", "warn", "danger"} else "ok"
    return (
        f'<div class="ecoscan-status-item ecoscan-status-{tone}">'
        f"<span>{html.escape(label)}</span>"
        f"<strong>{html.escape(value)}</strong>"
        f"<small>{html.escape(detail)}</small>"
        "</div>"
    )


def _service_chip(label: str) -> str:
    return f'<span class="ecoscan-service-chip">{html.escape(label)}</span>'


def _asset_data_uri(project_root: Path, relative_path: str) -> str:
    path = project_root / relative_path
    try:
        suffix = path.suffix.lower()
        mime = "image/png" if suffix == ".png" else "image/jpeg"
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return ""
    return f"data:{mime};base64,{payload}"


def _hero_recycle_visual(project_root: Path, active_profile: UserProfile) -> str:
    if active_profile.is_admin:
        items = [
            ("assets/disposal_targets/electronic_orange_dropoff.png", "Eletrônicos", "logística reversa"),
            ("assets/disposal_targets/glass_green_bin.png", "Vidro", "coleta seletiva"),
            ("assets/disposal_targets/lamp_orange_dropoff.png", "Lâmpadas", "coleta especial"),
        ]
        center_title = "Gestão"
        center_subtitle = "dados para melhorar a coleta"
    else:
        items = [
            ("assets/disposal_targets/plastic_red_bin.png", "Plástico", "lixeira vermelha"),
            ("assets/disposal_targets/paper_blue_bin.png", "Papel", "lixeira azul"),
            ("assets/disposal_targets/battery_orange_dropoff.png", "Pilhas", "ponto especial"),
        ]
        center_title = "Reciclar"
        center_subtitle = "começa pela foto"

    tiles = [
        """
        <div class="ecoscan-recycle-center">
            <div class="ecoscan-recycle-symbol">&#9851;</div>
            <strong>{title}</strong>
            <small>{subtitle}</small>
        </div>
        """.format(title=html.escape(center_title), subtitle=html.escape(center_subtitle))
    ]
    for relative_path, label, detail in items:
        source = _asset_data_uri(project_root, relative_path)
        image_html = f'<img src="{source}" alt="">' if source else ""
        tiles.append(
            '<div class="ecoscan-recycle-tile">'
            f"{image_html}"
            "<div>"
            f"<span>{html.escape(label)}</span>"
            f"<small>{html.escape(detail)}</small>"
            "</div>"
            "</div>"
        )
    return '<div class="ecoscan-recycle-visual">' + "".join(tiles) + "</div>"


def _render_institutional_hero(st: Any, config: Any, active_profile: UserProfile, campaign: Campaign | None) -> None:
    from ecoscan.ui.citizen_design import render_citizen_design
    render_citizen_design(st, _asset_data_uri(config.project_root, "assets/disposal_targets/plastic_red_bin.png"), admin=True)


def _render_user_flow_strip(st: Any) -> None:
    st.markdown(
        """
        <div class="ecoscan-user-flow">
            <div data-step="1"><span>Primeiro passo</span><strong>Abra a câmera e enquadre o resíduo</strong></div>
            <div data-step="2"><span>Resposta</span><strong>Veja lixeira, preparo e risco ambiental</strong></div>
            <div data-step="3"><span>Destino</span><strong>Procure ponto de coleta próximo</strong></div>
            <div data-step="4"><span>Participação</span><strong>Registre missão ou denúncia quando fizer sentido</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_public_overview_strip(st: Any) -> None:
    strip = "".join(
        [
            _status_item("Foto", "do resíduo", "captura ou galeria", "ok"),
            _status_item("Resposta", "descarte certo", "lixeira, preparo e impacto", "ok"),
            _status_item("Mapa", "coleta próxima", "busca rápida por material", "ok"),
            _status_item("Participação", "missões e pontos", "campanha ambiental ativa", "ok"),
        ]
    )
    st.markdown(f'<section class="ecoscan-status-strip">{strip}</section>', unsafe_allow_html=True)


def _public_code(code: str) -> str:
    return code.replace("APS-", "ECO-")


def _public_ui_text(value: str) -> str:
    replacements = {
        "APS": "Recicla SP",
        "no dataset bruto": "na base bruta de imagens",
        "No dataset bruto": "Na base bruta de imagens",
        "o dataset curado": "a base curada de imagens",
        "O dataset curado": "A base curada de imagens",
        "o dataset bruto": "a base bruta de imagens",
        "O dataset bruto": "A base bruta de imagens",
        "do dataset": "da base de imagens",
        "Do dataset": "Da base de imagens",
        "no dataset": "na base de imagens",
        "No dataset": "Na base de imagens",
        "Dataset bruto": "Base bruta de imagens",
        "dataset bruto": "base bruta de imagens",
        "Dataset curado": "Base curada de imagens",
        "dataset curado": "base curada de imagens",
        "Dataset": "Base de imagens",
        "dataset": "base de imagens",
        "acadêmica": "técnica",
        "acadêmico": "técnico",
        "acadêmicas": "técnicas",
        "acadêmicos": "técnicos",
        "Professor": "Usuário",
        "professor": "usuário",
        "Score": "Confiança",
        "score": "confiança",
    }
    text = value
    for old, new in replacements.items():
        text = text.replace(old, new)
    fixups = {
        "Modelo inicial avaliada": "Modelo inicial avaliado",
        "modelo inicial avaliada": "modelo inicial avaliado",
        "Tratar a modelo inicial": "Tratar o modelo inicial",
        "a modelo inicial": "o modelo inicial",
        "o base curada de imagens": "a base curada de imagens",
        "o base bruta de imagens": "a base bruta de imagens",
        "a base curada de imagens ainda está vazio": "a base curada de imagens ainda está vazia",
        "a base bruta de imagens ainda está vazio": "a base bruta de imagens ainda está vazia",
        "no base bruta de imagens": "na base bruta de imagens",
        "salvo no base bruta de imagens": "salvo na base bruta de imagens",
        "supero modelo inicial": "supera o modelo inicial",
        "histórico e status": "histórico e sistema",
    }
    for old, new in fixups.items():
        text = text.replace(old, new)
    return text


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


def _render_live_camera_link(st: Any) -> None:
    configured_live_url = os.environ.get("ECOSCAN_LIVE_URL", "").strip()
    live_url = configured_live_url or "http://localhost:8765/"
    st.link_button(
        "Escanear com câmera traseira",
        live_url,
        icon=":material/photo_camera:",
        width="stretch",
    )
    if configured_live_url:
        st.caption("Modo ao vivo em backend HTTPS dedicado.")
    else:
        st.caption(
            "O endereço local funciona com o servidor de câmera iniciado neste computador. "
            "No app público, use a captura de foto abaixo."
        )


def _render_capture_tips(st: Any) -> None:
    tips = "".join(f"<li>{html.escape(tip)}</li>" for tip in capture_photo_tips())
    st.markdown(
        f"""
        <div class="ecoscan-admin-panel">
            <strong>Para reconhecer melhor</strong>
            <ul>{tips}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_recognition_feedback_form(
    st: Any,
    config: Any,
    result: Any,
    active_profile: UserProfile,
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    from ecoscan.ui.learning import render_contribution
    render_contribution(st, config, result, active_profile)


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
                "python scripts\\prepare_delivery_pack.py",
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


def _render_collection_points_tab(
    st: Any,
    config: Any,
    guidance_by_class: dict[str, DisposalGuidance],
    collection_points: list[CollectionPoint],
) -> None:
    from ecoscan.ui.collection_map import render_collection_map
    render_collection_map(st, collection_points, guidance_by_class)


def _render_campaign_cards(st: Any, campaign: Campaign, guidance_by_class: dict[str, DisposalGuidance]) -> None:
    cards = []
    for mission in campaign.missions:
        classes = _campaign_class_labels(mission.target_classes, guidance_by_class, limit=4)
        cards.append(
            '<div class="ecoscan-mission-card">'
            f"<strong>{html.escape(mission.title)}</strong>"
            f"<span>{html.escape(mission.description)}</span>"
            f'<span class="ecoscan-card-meta">{mission.points} pontos'
            f"{' · ' + html.escape(classes) if classes else ''}</span>"
            "</div>"
        )
    st.markdown('<div class="ecoscan-card-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def _render_reward_cards(st: Any, campaign: Campaign) -> None:
    if not campaign.rewards:
        return
    cards = [
        '<div class="ecoscan-reward-card">'
        f"<strong>{html.escape(reward.title)}</strong>"
        f"<span>{html.escape(reward.description)}</span>"
        f'<span class="ecoscan-card-meta">a partir de {reward.points_required} pontos</span>'
        "</div>"
        for reward in campaign.rewards
    ]
    st.markdown('<div class="ecoscan-card-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def _campaign_class_labels(
    class_ids: tuple[str, ...],
    guidance_by_class: dict[str, DisposalGuidance],
    *,
    limit: int = 5,
) -> str:
    from ecoscan.services.operations import format_class_labels

    return format_class_labels(class_ids, _guidance_class_labels(guidance_by_class), limit=limit)


def _guidance_class_labels(guidance_by_class: dict[str, DisposalGuidance]) -> dict[str, str]:
    return {class_id: guidance.display_name for class_id, guidance in guidance_by_class.items()}


def _html_list(items: tuple[str, ...] | list[str], *, empty_text: str = "Não configurado.") -> str:
    clean_items = [str(item).strip() for item in items if str(item).strip()]
    if not clean_items:
        return f'<p class="ecoscan-muted">{html.escape(empty_text)}</p>'
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in clean_items) + "</ul>"


def _mission_label(mission: Mission) -> str:
    return f"{mission.title} · {mission.points} pontos"


def _role_label(role: str) -> str:
    labels = {"user": "cidadão", "admin": "gestão"}
    return labels.get(role, role)


def _profile_label(profile: UserProfile) -> str:
    organization = f" · {profile.organization}" if profile.organization else ""
    role = _role_label(profile.role)
    if profile.display_name.strip().lower() == role:
        return f"{profile.display_name}{organization}"
    return f"{profile.display_name} · {role}{organization}"


def _render_active_profile_card(st: Any, profile: UserProfile) -> None:
    mode = "Gestão" if profile.is_admin else "Cidadão"
    note = profile.notes or "Perfil local do protótipo."
    st.markdown(
        f"""
        <div class="ecoscan-profile-card">
            <strong>{html.escape(profile.display_name)}</strong>
            <span>{html.escape(mode)} · {html.escape(profile.organization or "Recicla SP")}</span>
            <span>{html.escape(note)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _next_reward_text(campaign: Campaign, points: int) -> str:
    next_reward = next((reward for reward in sorted(campaign.rewards, key=lambda r: r.points_required)
                        if reward.kind == "digital_badge" and reward.points_required > points), None)
    if next_reward:
        return f"Próxima recompensa: {next_reward.title} ({next_reward.points_required} pontos)."
    return "Consulte seus selos e os critérios de cada incentivo abaixo."


def _render_campaign_tab(
    st: Any,
    config: Any,
    campaign: Campaign | None,
    active_profile: UserProfile,
    guidance_by_class: dict[str, DisposalGuidance],
    impacts_by_class: dict[str, EnvironmentalImpact],
    targets_by_class: dict[str, DisposalTarget],
    pipeline_options: ProcessingPipelineOptions,
) -> None:
    st.markdown('<div class="ecoscan-section-title">Campanha ambiental</div>', unsafe_allow_html=True)
    if campaign is None:
        st.info("Campanha ainda não configurada.")
        return

    ledger_path = points_ledger_path_from_config(config)
    from ecoscan.services.operational_store import operations_enabled
    if not operations_enabled():
        st.caption("Piloto: a pontuação ainda usa armazenamento local temporário.")
    try:
        points = total_points_for_user(ledger_path, active_profile.id)
    except OSError as exc:
        st.error(str(exc))
        return
    info_cols = st.columns([1.2, 0.8])
    with info_cols[0]:
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
    with info_cols[1]:
        st.metric("Seus pontos", points)
        st.caption(_next_reward_text(campaign, points))

    st.markdown('<div class="ecoscan-section-title">Sua próxima ação</div>', unsafe_allow_html=True)
    st.caption("Uma pontuação por missão e conta. As atividades identificam materiais; não comprovam entrega. Na área Aprender, complete também os desafios educativos.")

    mission_col, proof_col = st.columns([0.95, 1.05])
    with mission_col:
        selected_mission = st.selectbox(
            "Missão para validar",
            campaign.missions,
            format_func=_mission_label,
            key="campaign_selected_mission",
        )
        st.info(selected_mission.proof_hint)
        st.write(selected_mission.description)
    with proof_col:
        requires_review = selected_mission.verification_action != "recognize_waste"
        if requires_review:
            st.info("Envie esta ocorrência pela área Denunciar. Ela exige análise da secretaria e não recebe pontos automaticamente por reconhecimento de imagem.")
        proof_source = st.radio("Comprovação", ["Câmera", "Imagem"], horizontal=True, key="campaign_proof_source")
        if proof_source == "Câmera":
            proof_file = st.camera_input("Fotografar missão", key="campaign_camera")
        else:
            proof_file = st.file_uploader(
                "Enviar foto da missão",
                type=["jpg", "jpeg", "png"],
                key="campaign_upload",
            )

        if proof_file is None:
            st.caption("Fotografe ou envie uma evidência da missão para liberar a validação.")
        is_visitor = active_profile.id.startswith("visitor_")
        if is_visitor:
            st.info("Entre em uma conta para registrar a participação e acumular pontos. Você pode consultar as missões sem login.")
        if st.button("Validar missão", disabled=proof_file is None or is_visitor or requires_review):
            temp_path = _temporary_upload(proof_file, prefix="mission")
            evidence_sha256 = hashlib.sha256(proof_file.getvalue()).hexdigest()
            try:
                with st.spinner("Validando missão com processamento de imagem..."):
                    from ecoscan.services.analysis_service import analyze_waste_image
                    mission_result = analyze_waste_image(temp_path, config, options=pipeline_options)
                evaluation = evaluate_mission_submission(selected_mission, mission_result)
                st.session_state["last_mission_result"] = mission_result
                st.session_state["last_mission_evaluation"] = evaluation
                if evaluation.accepted:
                    from ecoscan.services.engagement import award_once
                    award_once(
                        ledger_path, user_id=active_profile.id, mission_id=selected_mission.id,
                        points=evaluation.points_awarded, detected_class=evaluation.detected_class,
                        probability=evaluation.probability,
                        note=evaluation.reason + " Foto SHA-256: " + evidence_sha256,
                    )
                    updated_points = total_points_for_user(ledger_path, active_profile.id)
                    st.success(f"+{evaluation.points_awarded} pontos educativos. Total: {updated_points}.")
                else:
                    st.warning(evaluation.reason)
            except Exception as exc:
                _render_user_error(st, exc, context="campaign_mission")
            finally:
                Path(temp_path).unlink(missing_ok=True)

    evaluation = st.session_state.get("last_mission_evaluation")
    mission_result = st.session_state.get("last_mission_result")
    if (evaluation is not None and mission_result is not None
            and evaluation.mission_id == selected_mission.id):
        status_label = "validada" if evaluation.accepted else "pendente"
        st.markdown(
            f"""
            <div class="ecoscan-report-status {'inconclusivo' if not evaluation.accepted else ''}">
                <strong>Resultado da missão: {html.escape(status_label)}</strong>
                <span>{html.escape(evaluation.reason)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _render_photo_processing_summary(st, mission_result.pipeline)

    st.markdown('<div class="ecoscan-section-title">Recompensas e incentivo</div>', unsafe_allow_html=True)
    from ecoscan.ui.rewards import render_rewards
    try:
        current_points = total_points_for_user(ledger_path, active_profile.id)
    except OSError as exc:
        st.error(str(exc))
    else:
        render_rewards(st, campaign, current_points, active_profile)

    st.markdown('<div class="ecoscan-section-title">Guia educativo rápido</div>', unsafe_allow_html=True)
    guide_class = st.selectbox(
        "Material para orientar",
        list(guidance_by_class.keys()),
        format_func=lambda class_id: guidance_by_class[class_id].display_name,
        key="campaign_guide_class",
    )
    guidance = guidance_by_class.get(guide_class)
    impact = impacts_by_class.get(guide_class)
    target = targets_by_class.get(guide_class)
    if guidance:
        guide_cols = st.columns(3)
        guide_cols[0].write(f"**Como descartar:** {guidance.guidance}")
        guide_cols[1].write(f"**Por que importa:** {guidance.educational_note}")
        if target:
            guide_cols[2].write(f"**Destino:** {target.destination_title}")
        if impact:
            _render_environmental_impact(st, impact)


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


def _render_account_tab(
    st: Any,
    config: Any,
    active_profile: UserProfile,
    campaign: Campaign | None,
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    from ecoscan.ui.learning import render_citizen_protocols
    st.markdown('<div class="ecoscan-section-title">Minha participação</div>', unsafe_allow_html=True)
    _render_active_profile_card(st, active_profile)
    from ecoscan.services.release_info import release_info
    release = release_info()
    revision = (release["code_revision"] or "indisponível")[:12]
    st.caption(f"Recicla SP {release['app_version']} · Revisão {revision}")
    render_citizen_protocols(st, config, active_profile)
    if active_profile.id.startswith("visitor_"):
        return
    ledger_path = points_ledger_path_from_config(config)
    try:
        points = total_points_for_user(ledger_path, active_profile.id)
        transactions = read_point_transactions(ledger_path, user_id=active_profile.id, limit=20)
    except OSError as exc:
        st.error(str(exc))
        return

    cols = st.columns(3)
    cols[0].metric("Pontos acumulados", points)
    cols[1].metric("Missões validadas", len(transactions))
    cols[2].metric("Missões disponíveis", len(campaign.missions) if campaign else 0)
    if campaign:
        st.caption(_next_reward_text(campaign, points))

    if transactions:
        rows = [
            {
                "data_utc": transaction.timestamp_utc,
                "missão": transaction.mission_id,
                "pontos": transaction.points,
                "classe": transaction.detected_class,
                "confiança": transaction.probability,
                "status": transaction.status,
            }
            for transaction in reversed(transactions)
        ]
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("Este perfil ainda não possui missões pontuadas.")

    _render_field_test_form(st, config, active_profile, guidance_by_class)

    from ecoscan.ui.community import render_reports
    render_reports(st, key="profile_reports")


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


def _input_signature(uploaded_file: Any, source_kind: str, options: ProcessingPipelineOptions) -> str:
    from ecoscan.image_processing.contracts import PROCESSING_VERSION

    data = uploaded_file.getvalue()
    payload = {
        "processing_version": PROCESSING_VERSION,
        "source_kind": source_kind,
        "name": uploaded_file.name,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "options": {
            "filter_name": options.filter_name,
            "filter_parameters": options.filter_parameters or {},
            "segmentation_name": options.segmentation_name,
            "segmentation_parameters": options.segmentation_parameters or {},
            "morphology_name": options.morphology_name,
            "morphology_parameters": options.morphology_parameters or {},
        },
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _temporary_upload(uploaded_file: Any, prefix: str = "upload") -> Path:
    suffix = Path(uploaded_file.name or "upload.png").suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, prefix=f"ecoscan_{prefix}_", suffix=suffix) as temp_file:
        temp_file.write(uploaded_file.getbuffer())
        return Path(temp_file.name)


def main(*, page_configured=False) -> None:
    import streamlit as st

    from ecoscan.ui.processing_lab import select_morphology_parameters

    config = load_config()
    configure_logging(config.directories["logs"])
    resources = load_app_resources(config)
    guidance_by_class = resources.guidance_by_class
    targets_by_class = resources.targets_by_class
    impacts_by_class = resources.impacts_by_class
    requirements_by_class = resources.requirements_by_class
    collection_points = resources.collection_points
    profiles = resources.profiles
    if not page_configured:
        st.set_page_config(page_title="Recicla SP", layout="wide", initial_sidebar_state="collapsed")
    _render_theme(st)
    campaign = None  # Public entry must not wait for the campaign database.

    from ecoscan.app.processing_options import default_processing_options
    defaults = default_processing_options(config)
    filter_name = defaults.filter_name
    filter_parameters: dict[str, Any] = {}
    segmentation_name = defaults.segmentation_name
    segmentation_parameters: dict[str, Any] = {}
    morphology_name = defaults.morphology_name
    morphology_parameters: dict[str, Any] = {}
    save_history = False

    active_profile = render_identity(st)
    with st.sidebar:
        st.header("Identificação")
        _render_active_profile_card(st, active_profile)

        if active_profile.is_admin:
            st.header("Operação da Secretaria")
            _render_model_status(st, config)

            st.header("Parâmetros técnicos")
            filter_name = st.selectbox(
                "Filtro",
                FILTERS,
                index=FILTERS.index(defaults.filter_name),
            )
            filter_parameters = select_filter_parameters(st, filter_name, config)

            segmentation_name = st.selectbox(
                "Segmentação",
                SEGMENTATIONS,
                index=SEGMENTATIONS.index(defaults.segmentation_name),
            )
            segmentation_parameters = select_segmentation_parameters(st, segmentation_name)
            morphology_name, morphology_parameters = select_morphology_parameters(st, config.segmentation.get("morphology"))
            save_history = st.checkbox("Salvar no histórico local", value=False)
        else:
            st.header("Atendimento")
            st.caption("Use o laboratório na página para comparar técnicas de processamento.")

    if not active_profile.is_admin:
        _render_public_app_chrome(st)

    if active_profile.is_admin:
        _render_institutional_hero(st, config, active_profile, campaign)
    else:
        from ecoscan.ui.citizen_design import render_citizen_design
        render_citizen_design(st, _asset_data_uri(config.project_root, "assets/disposal_targets/plastic_red_bin.png"))
    st.caption("Recicla SP · piloto independente de educação ambiental. Não é um canal oficial de atendimento municipal.")
    if active_profile.is_admin:
        render_scope(st)
    else:
        with st.expander("Laboratório de processamento de imagens"):
            st.caption("Compare técnicas da disciplina. Alterar parâmetros reprocessa a foto carregada.")
            filter_name = st.selectbox(
                "Filtro",
                FILTERS,
                index=FILTERS.index(defaults.filter_name),
                key="public_filter",
            )
            filter_parameters = select_filter_parameters(st, filter_name, config)
            segmentation_name = st.selectbox(
                "Segmentação",
                SEGMENTATIONS,
                index=SEGMENTATIONS.index(defaults.segmentation_name),
                key="public_segmentation",
            )
            segmentation_parameters = select_segmentation_parameters(st, segmentation_name)
            morphology_name, morphology_parameters = select_morphology_parameters(st, config.segmentation.get("morphology"))
            if not active_profile.id.startswith("visitor_"):
                save_history = st.checkbox("Salvar no histórico local", value=False, key="public_history")


    class_chips = "".join(_class_chip(class_id, guidance_by_class) for class_id in config.classes)

    pipeline_options = ProcessingPipelineOptions(
        filter_name=filter_name,
        filter_parameters=filter_parameters,
        segmentation_name=segmentation_name,
        segmentation_parameters=segmentation_parameters,
        morphology_name=morphology_name,
        morphology_parameters=morphology_parameters,
    )

    navigation = navigation_for(admin=active_profile.is_admin)
    tabs = dict(zip(navigation.tabs, st.tabs(
        navigation.tabs, key="main_navigation_" + active_profile.role, on_change="rerun")))
    if any(tabs[name].open for name in (navigation.campaign, navigation.account, "Gestão") if name in tabs):
        campaign = _load_campaign_config(config)
    result = st.session_state.get("last_analysis_result")

    if tabs["Aprender"].open:
        with tabs["Aprender"]:
            render_education(st, config.project_root, active_profile, points_ledger_path_from_config(config))

    if "Descarte" in tabs and tabs["Descarte"].open:
        with tabs["Descarte"]:
            st.subheader("Descarte responsável")
            render_scope(st)

    with tabs[navigation.analysis]:
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
            if st.session_state.get("last_analysis_signature") != signature:
                for stale_key in ("last_analysis_result", "last_analysis_signature", "last_analysis_source"):
                    st.session_state.pop(stale_key, None)
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
                    st.session_state["last_analysis_result"] = result
                    st.session_state["last_analysis_signature"] = signature
                    st.session_state["last_analysis_source"] = source_kind
                except Exception as exc:
                    result = None
                    _render_user_error(st, exc, context="image_analysis")
                finally:
                    if temp_path is not None:
                        try:
                            temp_path.unlink(missing_ok=True)
                        except OSError:
                            LOGGER.warning("temporary_upload_cleanup_failed")
            else:
                result = st.session_state.get("last_analysis_result")

            if result is not None:
                should_save_history = not active_profile.id.startswith("visitor_") and (
                    bool(config.history.get("enabled", True)) or save_history)
                if should_save_history and st.session_state.get("last_history_saved_signature") != signature:
                    try:
                        from ecoscan.services.history import (
                            append_history_entry,
                            build_history_entry,
                            history_path_from_config,
                        )

                        append_history_entry(
                            history_path_from_config(config),
                            build_history_entry(result, source_path=st.session_state.get("last_analysis_source")),
                        )
                        st.session_state["last_history_saved_signature"] = signature
                    except OSError:
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
                render_applied_processing(st, result.pipeline)

                left, right = st.columns([1.05, 1])
                with left:
                    st.image(result.pipeline.loaded.array, caption="Imagem analisada", width="stretch")
                with right:
                    st.markdown('<div class="ecoscan-result">', unsafe_allow_html=True)
                    _render_recognition_decision(st, safety_decision)
                    if result.model_type == "semantic_onnx_assisted":
                        if suggested_guidance is not None and safety_decision.status == "needs_confirmation":
                            st.subheader("Material sugerido: " + suggested_guidance.display_name)
                            if suggested_target is not None:
                                st.write(
                                    f"**Destino para {suggested_guidance.display_name}: "
                                    f"{suggested_target.destination_title}.**"
                                )
                            st.caption("Confira a composição e o conteúdo da embalagem antes de escolher a orientação.")
                        else:
                            st.subheader("Selecione o material para consultar o descarte")
                            st.write("Você pode identificar o material manualmente na lista abaixo.")
                    elif result.accepted and result.guidance and safety_decision.allow_disposal_guidance:
                        st.subheader("Material sugerido: " + result.guidance.display_name)
                        st.write(f"**Categoria ambiental:** {result.guidance.environmental_category}")
                    else:
                        st.subheader("Escolha o material da foto")
                        st.write("Se necessário, tire outra foto em boa iluminação e com o objeto centralizado.")
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

                st.markdown(
                    '<div class="ecoscan-section-title">Confirme o material e veja o descarte</div>',
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
                    help="Escolha a categoria do material. A foto não determina composição ou contaminação.",
                )
                if confirmed_class is not None:
                    confirmed_guidance = guidance_by_class.get(confirmed_class)
                    confirmed_target = targets_by_class.get(confirmed_class)
                    confirmed_impact = impacts_by_class.get(confirmed_class)
                    if confirmed_guidance is not None and confirmed_target is not None:
                        st.success(
                            f"{confirmed_guidance.display_name}: "
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

    if tabs[navigation.campaign].open:
        with tabs[navigation.campaign]:
            _render_campaign_tab(
                st,
                config,
                campaign,
                active_profile,
                guidance_by_class,
                impacts_by_class,
                targets_by_class,
                pipeline_options,
            )

    if tabs[navigation.report].open:
        with tabs[navigation.report]:
            _render_civic_reports_tab(st, config, active_profile, pipeline_options)

    if tabs[navigation.collection].open:
        with tabs[navigation.collection]:
            _render_collection_points_tab(st, config, guidance_by_class, collection_points)

    if "Processamento" in tabs and tabs["Processamento"].open:
        with tabs["Processamento"]:
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

    if "Base de imagens" in tabs and tabs["Base de imagens"].open:
        with tabs["Base de imagens"]:
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
                        st.session_state["dataset_ingestion_results"] = [result.__dict__ for result in results]
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

            _render_ingestion_results(st, st.session_state.get("dataset_ingestion_results", []))
            st.markdown('<div class="ecoscan-section-title">Prontidão para treino</div>', unsafe_allow_html=True)
            _render_dataset_readiness(st, config)
            st.markdown('<div class="ecoscan-section-title">Resumo da base de imagens</div>', unsafe_allow_html=True)
            _render_dataset_status(st, config, guidance_by_class)

    if "Histórico" in tabs and tabs["Histórico"].open:
        with tabs["Histórico"]:
            _render_history(st, config)

    if tabs[navigation.account].open:
        with tabs[navigation.account]:
            _render_account_tab(st, config, active_profile, campaign, guidance_by_class)

    if active_profile.is_admin and tabs["Gestão"].open:
        with tabs["Gestão"]:
            _render_admin_tab(
                st,
                config,
                active_profile,
                profiles,
                campaign,
                collection_points,
                guidance_by_class,
            )

    if "Conclusão" in tabs and tabs["Conclusão"].open:
        with tabs["Conclusão"]:
            st.markdown('<div class="ecoscan-section-title">Conclusão e prontidão final</div>', unsafe_allow_html=True)
            _render_completion_panel(st, config)
            _render_model_governance(st, config, guidance_by_class)

    if "Sistema" in tabs and tabs["Sistema"].open:
        with tabs["Sistema"]:
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


if __name__ == "__main__":
    main()
