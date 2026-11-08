"""Disposal and recycling presentation components.

Domain mappings come from ecoscan.disposal and are not recalculated by the view.
"""
from __future__ import annotations

import html
from typing import Any

from ecoscan.disposal.collection_points import (
    CollectionPoint,
    build_collection_point_directions_url,
    build_collection_point_map_url,
    filter_collection_points,
    rank_collection_points,
)
from ecoscan.disposal.guidance import DisposalGuidance
from ecoscan.disposal.impact import EnvironmentalImpact
from ecoscan.disposal.targets import DisposalTarget, build_map_search_url
from ecoscan.services.photo_requirements import PhotoRequirement
from ecoscan.services.public_flow import PublicNextAction
from ecoscan.services.recognition_safety import RecognitionSafetyDecision


def _render_environmental_impact(st: Any, impact: EnvironmentalImpact | None) -> None:
    if impact is None:
        return

    risk_level = impact.risk_level.lower().strip()
    if risk_level not in {"baixo", "moderado", "alto"}:
        risk_level = "moderado"
    risks = "".join(f"<li>{html.escape(risk)}</li>" for risk in impact.bad_disposal_risks[:3])
    st.markdown(
        f"""
        <div class="ecoscan-impact-panel {html.escape(risk_level)}">
            <div class="ecoscan-impact-head">
                <strong>{html.escape(impact.impact_title)}</strong>
                <span class="ecoscan-risk-tag">{html.escape(impact.risk_label)}</span>
            </div>
            <ul>{risks}</ul>
            <p class="ecoscan-positive-action">{html.escape(impact.positive_action)}</p>
            <a class="ecoscan-source-link" href="{html.escape(impact.source_url)}" target="_blank" rel="noopener noreferrer">
                Fonte de referência: {html.escape(impact.source_label)}
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _format_point_materials(point: CollectionPoint, *, limit: int = 5) -> str:
    materials = list(point.accepted_materials[:limit])
    suffix = "" if len(point.accepted_materials) <= limit else "..."
    return ", ".join(materials) + suffix


def _render_collection_point_cards(
    st: Any,
    points: list[CollectionPoint],
    *,
    origin: str | None = None,
    limit: int = 3,
) -> None:
    if not points:
        st.info("Nenhum ponto cadastrado para esse material na base local. Use a busca no mapa ou cadastre pontos oficiais em config/collection_points.json.")
        return

    ranked = rank_collection_points(points, limit=limit)
    cards: list[str] = []
    for item in ranked:
        point = item.point
        distance = f"{item.distance_km:.2f} km" if item.distance_km is not None else "distância via Maps"
        map_url = build_collection_point_map_url(point)
        directions_url = build_collection_point_directions_url(point, origin=origin)
        materials = _format_point_materials(point)
        cards.append(
            '<div class="ecoscan-point-card">'
            f"<strong>{html.escape(point.name)}</strong>"
            f"<span>{html.escape(point.full_address)}</span>"
            f"<span>{html.escape(point.hours)} · {html.escape(distance)}</span>"
            f'<span class="ecoscan-point-materials">{html.escape(materials)}</span>'
            '<div class="ecoscan-point-actions">'
            f'<a class="primary" href="{html.escape(directions_url)}" target="_blank" rel="noopener noreferrer">Traçar rota</a>'
            f'<a href="{html.escape(map_url)}" target="_blank" rel="noopener noreferrer">Ver no mapa</a>'
            "</div>"
            "</div>"
        )
    st.markdown(
        '<div class="ecoscan-point-list">' + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )


def _render_photo_requirement_plan(st: Any, requirement: PhotoRequirement | None) -> None:
    if requirement is None:
        st.info("Plano de fotos ainda não configurado para esta classe.")
        return

    examples = "".join(f"<li>{html.escape(item)}</li>" for item in requirement.examples[:7])
    contexts = "".join(f"<li>{html.escape(item)}</li>" for item in requirement.contexts[:5])
    avoid = "".join(f"<li>{html.escape(item)}</li>" for item in requirement.avoid[:5])
    st.markdown(
        f"""
        <div class="ecoscan-photo-plan">
            <h4>{html.escape(requirement.title)}</h4>
            <div class="ecoscan-photo-plan-meta">
                <div>
                    <span>Mínimo por classe</span>
                    <strong>{requirement.minimum_images}</strong>
                </div>
                <div>
                    <span>Ideal para treino</span>
                    <strong>{requirement.ideal_images}</strong>
                </div>
            </div>
            <strong>Fotos para procurar</strong>
            <ul class="ecoscan-photo-plan-list">{examples}</ul>
            <strong>Variações importantes</strong>
            <ul class="ecoscan-photo-plan-list">{contexts}</ul>
            <strong>Evitar no lote</strong>
            <ul class="ecoscan-photo-plan-list">{avoid}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_disposal_action_panel(
    st: Any,
    config: Any,
    guidance: DisposalGuidance,
    target: DisposalTarget | None,
    impact: EnvironmentalImpact | None,
    collection_points: list[CollectionPoint],
) -> None:
    if target is None:
        st.info("Orientação visual de descarte ainda não configurada para esta classe.")
        return

    st.markdown('<div class="ecoscan-section-title">Próximo passo de descarte</div>', unsafe_allow_html=True)
    visual_col, action_col = st.columns([0.95, 1.05])
    with visual_col:
        asset_path = target.asset_absolute_path(config.project_root)
        if asset_path.exists():
            st.image(str(asset_path), caption=target.destination_title, width="stretch")
        else:
            st.markdown(
                f"""
                <div class="ecoscan-disposal-panel">
                    <div class="ecoscan-disposal-title">
                        <span class="ecoscan-color-dot" style="background:{html.escape(target.bin_color_hex)}"></span>
                        {html.escape(target.destination_title)}
                    </div>
                    <p class="ecoscan-muted">{html.escape(target.destination_type)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with action_col:
        steps = "".join(f"<li>{html.escape(step)}</li>" for step in target.preparation_steps)
        st.markdown(
            f"""
            <div class="ecoscan-disposal-panel featured">
                <div class="ecoscan-action-eyebrow">Destino recomendado</div>
                <div class="ecoscan-disposal-title">
                    <span class="ecoscan-color-dot" style="background:{html.escape(target.bin_color_hex)}"></span>
                    {html.escape(target.destination_title)}
                </div>
                <p>{html.escape(target.destination_type)}</p>
                <div class="ecoscan-destination-grid">
                    <div class="ecoscan-destination-tile">
                        <span>Material</span>
                        <strong>{html.escape(guidance.display_name)}</strong>
                    </div>
                    <div class="ecoscan-destination-tile">
                        <span>Categoria</span>
                        <strong>{html.escape(guidance.environmental_category)}</strong>
                    </div>
                    <div class="ecoscan-destination-tile">
                        <span>{"Cor da lixeira" if target.class_id in {"plastic", "paper_cardboard", "metal", "glass"} else "Tipo de destino"}</span>
                        <strong>{html.escape(target.bin_color_name if target.class_id in {"plastic", "paper_cardboard", "metal", "glass"} else "Ponto especial")}</strong>
                    </div>
                </div>
                <p class="ecoscan-muted">{html.escape(guidance.guidance)}</p>
                <ol class="ecoscan-step-list">{steps}</ol>
                <p class="ecoscan-muted"><strong>Atenção:</strong> {html.escape(target.attention_note)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        location_text = st.text_input(
            "Digite cidade, bairro ou CEP para buscar um ponto próximo",
            key=f"disposal_location_{target.class_id}",
            placeholder="ex.: Ribeirão Preto, SP ou 14000-000",
        )
        map_url = build_map_search_url(
            target.search_query,
            location_text if location_text else "perto de mim",
        )
        generic_map_url = build_map_search_url(
            "ecoponto coleta seletiva logística reversa resíduos",
            location_text if location_text else "perto de mim",
        )
        maps_col, ecopoint_col = st.columns(2)
        maps_col.link_button("Ponto específico", map_url, width="stretch")
        ecopoint_col.link_button("Ecopontos próximos", generic_map_url, width="stretch")
        st.caption("Os links de mapa precisam de internet. A orientação local permanece disponível. "
                   "Confirme horário, regras e materiais aceitos antes de levar o resíduo.")
    _render_environmental_impact(st, impact)
    matching_points = filter_collection_points(collection_points, class_id=target.class_id)
    if matching_points:
        st.markdown('<div class="ecoscan-section-title">Pontos cadastrados compatíveis</div>', unsafe_allow_html=True)
        _render_collection_point_cards(
            st,
            matching_points,
            origin=location_text or None,
            limit=3,
        )


def _render_recognition_decision(st: Any, decision: RecognitionSafetyDecision) -> None:
    renderer = {
        "ok": st.success,
        "warn": st.warning,
        "danger": st.error,
    }.get(decision.tone, st.info)
    renderer(f"{decision.title}. {decision.message} {decision.primary_action}")


def _render_public_next_action(st: Any, action: PublicNextAction) -> None:
    steps = "".join(f"<li>{html.escape(step)}</li>" for step in action.preparation_steps)
    st.markdown(
        f"""
        <section class="ecoscan-public-action {html.escape(action.tone)}">
            <div class="ecoscan-public-action-head">
                <div class="ecoscan-public-action-icon" style="background:{html.escape(action.bin_color_hex)}"></div>
                <div>
                    <strong>{html.escape(action.title)}</strong>
                    <span>{html.escape(action.message)}</span>
                </div>
            </div>
            <div class="ecoscan-public-action-body">
                <div class="ecoscan-public-action-grid">
                    <div class="ecoscan-public-action-tile">
                        <span>Material</span>
                        <strong>{html.escape(action.material_label)}</strong>
                    </div>

                    <div class="ecoscan-public-action-tile">
                        <span>Destino</span>
                        <strong>{html.escape(action.destination_title)}</strong>
                    </div>
                    <div class="ecoscan-public-action-tile">
                        <span>Orientação</span>
                        <strong>{html.escape(action.destination_type)}</strong>
                    </div>
                </div>
                <ol class="ecoscan-public-action-steps">{steps}</ol>
                <p class="ecoscan-public-action-note">{html.escape(action.attention_note)}</p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if action.can_search_collection and action.search_query:
        location_text = st.text_input(
            "Buscar ponto próximo",
            key="public_next_action_location",
            placeholder="Digite cidade, bairro ou CEP",
        )
        st.link_button(
            "Encontrar ponto de coleta",
            build_map_search_url(action.search_query, location_text if location_text else "perto de mim"),
            width="stretch",
        )


