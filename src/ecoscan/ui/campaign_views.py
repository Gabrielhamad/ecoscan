"""Campaign, learning missions and reward presentation.

The campaign service owns persistence, points and mission rules.
"""
from __future__ import annotations

import hashlib
import html
from pathlib import Path
from typing import Any

from ecoscan.app.processing_options import ProcessingPipelineOptions
from ecoscan.disposal.guidance import DisposalGuidance
from ecoscan.disposal.impact import EnvironmentalImpact
from ecoscan.disposal.targets import DisposalTarget
from ecoscan.services.accounts import (
    UserProfile, points_ledger_path_from_config, total_points_for_user,
)
from ecoscan.services.campaigns import Campaign, Mission, evaluate_mission_submission
from ecoscan.ui.common_views import _guidance_class_labels, _render_user_error
from ecoscan.ui.disposal_views import _render_environmental_impact
from ecoscan.ui.interaction_helpers import _temporary_upload
from ecoscan.ui.processing_views import _render_photo_processing_summary


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


def _mission_label(mission: Mission) -> str:
    return f"{mission.title} · {mission.points} pontos"


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


