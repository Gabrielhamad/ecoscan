from __future__ import annotations

import base64
import html
import logging
from pathlib import Path
from typing import Any

from ecoscan.config import load_config
from ecoscan.disposal.collection_points import CollectionPoint
from ecoscan.disposal.guidance import DisposalGuidance
from ecoscan.disposal.impact import (
    EnvironmentalImpact,
    get_environmental_impact,
)
from ecoscan.disposal.targets import DisposalTarget, get_disposal_target
from ecoscan.services.accounts import (
    UserProfile,
    points_ledger_path_from_config,
    read_point_transactions,
    total_points_for_user,
)
from ecoscan.services.campaigns import (
    Campaign,
    campaign_path_from_config,
    load_campaign,
)
from ecoscan.ui.app_resources import load_app_resources
from ecoscan.ui.education import render_education
from ecoscan.ui.identity import render_identity
from ecoscan.ui.scope import render_scope
from ecoscan.ui.analysis_widgets import (
    _render_capture_tips as _render_capture_tips,
    _render_live_camera_link as _render_live_camera_link,
    _render_recognition_feedback_form as _render_recognition_feedback_form,
)
from ecoscan.ui.analysis_controller import render_analysis_page
from ecoscan.ui.navigation_controller import build_navigation
from ecoscan.ui.processing_configuration import (
    render_public_lab_controls,
    render_sidebar_controls,
)
from ecoscan.ui.session_state import AnalysisSession
from ecoscan.ui.technical_page_controllers import (
    render_conclusion_page,
    render_dataset_page,
    render_processing_details_page,
    render_system_page,
)
from ecoscan.ui.interaction_helpers import (
    _input_signature as _input_signature,
    _temporary_upload as _temporary_upload,
)
from ecoscan.ui.campaign_views import (
    _render_campaign_cards as _render_campaign_cards,
    _render_reward_cards as _render_reward_cards,
    _campaign_class_labels as _campaign_class_labels,
    _mission_label as _mission_label,
    _next_reward_text as _next_reward_text,
    _render_campaign_tab as _render_campaign_tab,
)
from ecoscan.ui.civic_views import (
    _render_civic_report_status as _render_civic_report_status,
    _render_civic_reports_tab as _render_civic_reports_tab,
)
from ecoscan.ui.admin_views import (
    _render_field_test_form as _render_field_test_form,
    _render_admin_campaign_operations as _render_admin_campaign_operations,
    _render_admin_recognition_improvement_plan as _render_admin_recognition_improvement_plan,
    _render_admin_field_tests as _render_admin_field_tests,
    _render_admin_recognition_quality as _render_admin_recognition_quality,
    _render_admin_tab as _render_admin_tab,
)
from ecoscan.ui.common_views import (
    _badge as _badge,
    _render_user_error as _render_user_error,
    _class_label as _class_label,
    _status_item as _status_item,
    _public_code as _public_code,
    _public_ui_text as _public_ui_text,
    _guidance_class_labels as _guidance_class_labels,
    _html_list as _html_list,
)
from ecoscan.ui.system_views import (
    _render_overview_strip as _render_overview_strip,
    _render_model_status as _render_model_status,
    _dataset_rows as _dataset_rows,
    _render_dataset_status as _render_dataset_status,
    _render_dataset_readiness as _render_dataset_readiness,
    _render_ingestion_results as _render_ingestion_results,
    _render_dependencies as _render_dependencies,
    _render_access_testing_panel as _render_access_testing_panel,
    _render_error_catalog as _render_error_catalog,
    _render_free_hosting_panel as _render_free_hosting_panel,
    _completion_label as _completion_label,
    _render_completion_panel as _render_completion_panel,
    _render_final_readiness as _render_final_readiness,
    _model_governance_status_label as _model_governance_status_label,
    _render_model_governance as _render_model_governance,
    _render_delivery_pack as _render_delivery_pack,
    _render_acceptance_checks as _render_acceptance_checks,
    _render_aps_audit as _render_aps_audit,
    _render_history as _render_history,
)
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

LOGGER = logging.getLogger(__name__)


def _format_count(value: int, singular: str, plural: str | None = None) -> str:
    label = singular if value == 1 else (plural or f"{singular}s")
    return f"{value} {label}"


def _render_theme(st: Any) -> None:
    from ecoscan.ui.appearance import render_theme
    render_theme(st)


def _render_public_app_chrome(st: Any) -> None:
    st.markdown('<style>[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display:none}</style>', unsafe_allow_html=True)


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


def _class_chip(class_id: str, guidance_by_class: dict[str, DisposalGuidance]) -> str:
    guidance = guidance_by_class.get(class_id)
    label = guidance.display_name if guidance else class_id
    category = guidance.environmental_category if guidance else "classe ativa"
    return (
        '<span class="ecoscan-chip">'
        f"{html.escape(label)} <small>{html.escape(category)}</small>"
        "</span>"
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


def _render_collection_points_tab(
    st: Any,
    config: Any,
    guidance_by_class: dict[str, DisposalGuidance],
    collection_points: list[CollectionPoint],
) -> None:
    from ecoscan.ui.collection_map import render_collection_map
    render_collection_map(st, collection_points, guidance_by_class)


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


def main(*, page_configured: bool = False) -> None:
    """Compose authenticated navigation while delegating each page's behavior."""
    import streamlit as st

    config = load_config()
    configure_logging(config.directories["logs"])
    resources = load_app_resources(config)
    if not page_configured:
        st.set_page_config(page_title="Recicla SP", layout="wide", initial_sidebar_state="collapsed")
    _render_theme(st)

    active_profile = render_identity(st)
    selection = render_sidebar_controls(
        st,
        config,
        active_profile,
        render_profile=_render_active_profile_card,
        render_model_status=_render_model_status,
    )

    if not active_profile.is_admin:
        _render_public_app_chrome(st)
    if active_profile.is_admin:
        _render_institutional_hero(st, config, active_profile, None)
    else:
        from ecoscan.ui.citizen_design import render_citizen_design
        render_citizen_design(
            st, _asset_data_uri(config.project_root, "assets/disposal_targets/plastic_red_bin.png"),
        )
    st.caption("Recicla SP · piloto independente de educação ambiental. Não é um canal oficial de atendimento municipal.")
    if active_profile.is_admin:
        render_scope(st)
    else:
        selection = render_public_lab_controls(st, config, active_profile, selection)

    routing = build_navigation(st, active_profile)
    navigation, tabs = routing.spec, routing.tabs
    campaign = _load_campaign_config(config) if routing.campaign_required else None
    session = AnalysisSession(st.session_state)
    options = selection.to_options()

    if routing.open("Aprender"):
        with tabs["Aprender"]:
            render_education(
                st, config.project_root, active_profile, points_ledger_path_from_config(config),
            )
    if routing.open("Descarte"):
        with tabs["Descarte"]:
            st.subheader("Descarte responsável")
            render_scope(st)

    # Keep the photo widget mounted across navigation, as in the original flow.
    result = render_analysis_page(
        st, tabs[navigation.analysis], config, active_profile,
        resources.guidance_by_class, resources.targets_by_class, resources.impacts_by_class,
        resources.collection_points, options, selection.save_history, session,
    )

    if routing.open(navigation.campaign):
        with tabs[navigation.campaign]:
            _render_campaign_tab(
                st, config, campaign, active_profile, resources.guidance_by_class,
                resources.impacts_by_class, resources.targets_by_class, options,
            )
    if routing.open(navigation.report):
        with tabs[navigation.report]:
            _render_civic_reports_tab(st, config, active_profile, options)
    if routing.open(navigation.collection):
        with tabs[navigation.collection]:
            _render_collection_points_tab(
                st, config, resources.guidance_by_class, resources.collection_points,
            )

    if routing.open("Processamento"):
        render_processing_details_page(st, tabs["Processamento"], result)
    if routing.open("Base de imagens"):
        class_chips = "".join(
            _class_chip(class_id, resources.guidance_by_class) for class_id in config.classes
        )
        render_dataset_page(
            st, tabs["Base de imagens"], config, resources.guidance_by_class,
            resources.requirements_by_class, class_chips, session,
        )
    if routing.open("Histórico"):
        with tabs["Histórico"]:
            _render_history(st, config)

    if routing.open(navigation.account):
        with tabs[navigation.account]:
            _render_account_tab(
                st, config, active_profile, campaign, resources.guidance_by_class,
            )
    if active_profile.is_admin and routing.open("Gestão"):
        with tabs["Gestão"]:
            _render_admin_tab(
                st, config, active_profile, resources.profiles, campaign,
                resources.collection_points, resources.guidance_by_class,
            )
    if routing.open("Conclusão"):
        render_conclusion_page(st, tabs["Conclusão"], config, resources.guidance_by_class)
    if routing.open("Sistema"):
        render_system_page(st, tabs["Sistema"], config)


if __name__ == "__main__":
    main()
