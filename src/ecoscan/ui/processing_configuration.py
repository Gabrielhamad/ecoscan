"""Presentation-only configuration for filtering, segmentation and morphology.

Selections are values; they do not write application/session keys. The
classification and image-processing services remain responsible for execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ecoscan.app.processing_options import ProcessingPipelineOptions, default_processing_options
from ecoscan.services.accounts import UserProfile
from ecoscan.ui.processing_controls import (
    FILTERS,
    SEGMENTATIONS,
    select_filter_parameters,
    select_segmentation_parameters,
)


@dataclass(frozen=True)
class ProcessingSelection:
    filter_name: str
    filter_parameters: dict[str, Any] = field(default_factory=dict)
    segmentation_name: str = "auto"
    segmentation_parameters: dict[str, Any] = field(default_factory=dict)
    morphology_name: str = "none"
    morphology_parameters: dict[str, Any] = field(default_factory=dict)
    save_history: bool = False

    def to_options(self) -> ProcessingPipelineOptions:
        return ProcessingPipelineOptions(
            filter_name=self.filter_name,
            filter_parameters=self.filter_parameters,
            segmentation_name=self.segmentation_name,
            segmentation_parameters=self.segmentation_parameters,
            morphology_name=self.morphology_name,
            morphology_parameters=self.morphology_parameters,
        )


def _defaults(config: Any) -> ProcessingSelection:
    options = default_processing_options(config)
    return ProcessingSelection(
        filter_name=options.filter_name,
        segmentation_name=options.segmentation_name,
        morphology_name=options.morphology_name,
    )


def render_sidebar_controls(
    st: Any,
    config: Any,
    profile: UserProfile,
    *,
    render_profile: Callable[[Any, UserProfile], None],
    render_model_status: Callable[[Any, Any], None],
) -> ProcessingSelection:
    from ecoscan.ui.processing_lab import select_morphology_parameters

    defaults = _defaults(config)
    with st.sidebar:
        st.header("Identificação")
        render_profile(st, profile)

        if profile.is_admin:
            st.header("Operação da Secretaria")
            render_model_status(st, config)

            st.header("Parâmetros técnicos")
            filter_name = st.selectbox(
                "Filtro", FILTERS, index=FILTERS.index(defaults.filter_name),
            )
            filter_parameters = select_filter_parameters(st, filter_name, config)
            segmentation_name = st.selectbox(
                "Segmentação", SEGMENTATIONS,
                index=SEGMENTATIONS.index(defaults.segmentation_name),
            )
            segmentation_parameters = select_segmentation_parameters(st, segmentation_name)
            morphology_name, morphology_parameters = select_morphology_parameters(
                st, config.segmentation.get("morphology"),
            )
            save_history = st.checkbox("Salvar no histórico local", value=False)
            return ProcessingSelection(
                filter_name=filter_name,
                filter_parameters=filter_parameters,
                segmentation_name=segmentation_name,
                segmentation_parameters=segmentation_parameters,
                morphology_name=morphology_name,
                morphology_parameters=morphology_parameters,
                save_history=save_history,
            )

        st.header("Atendimento")
        st.caption("Use o laboratório na página para comparar técnicas de processamento.")
    return defaults


def render_public_lab_controls(
    st: Any,
    config: Any,
    profile: UserProfile,
    selection: ProcessingSelection,
) -> ProcessingSelection:
    """Keep existing public widget keys so a rerun preserves user selections."""
    if profile.is_admin:
        return selection

    from ecoscan.ui.processing_lab import select_morphology_parameters

    defaults = _defaults(config)
    with st.expander("Laboratório de processamento de imagens"):
        st.caption("Compare técnicas da disciplina. Alterar parâmetros reprocessa a foto carregada.")
        filter_name = st.selectbox(
            "Filtro", FILTERS, index=FILTERS.index(defaults.filter_name),
            key="public_filter",
        )
        filter_parameters = select_filter_parameters(st, filter_name, config)
        segmentation_name = st.selectbox(
            "Segmentação", SEGMENTATIONS,
            index=SEGMENTATIONS.index(defaults.segmentation_name),
            key="public_segmentation",
        )
        segmentation_parameters = select_segmentation_parameters(st, segmentation_name)
        morphology_name, morphology_parameters = select_morphology_parameters(
            st, config.segmentation.get("morphology"),
        )
        save_history = (
            st.checkbox("Salvar no histórico local", value=False, key="public_history")
            if not profile.id.startswith("visitor_") else False
        )
    return ProcessingSelection(
        filter_name=filter_name,
        filter_parameters=filter_parameters,
        segmentation_name=segmentation_name,
        segmentation_parameters=segmentation_parameters,
        morphology_name=morphology_name,
        morphology_parameters=morphology_parameters,
        save_history=save_history,
    )
