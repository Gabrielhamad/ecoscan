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
