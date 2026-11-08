"""Shared, side-effect-free presentation helpers and boundary error rendering.

No import from the Streamlit application coordinator; dependencies point inward.
"""
from __future__ import annotations

import html
import logging
from typing import Any

from ecoscan.disposal.guidance import DisposalGuidance

LOGGER = logging.getLogger(__name__)


def _badge(label: str, tone: str = "ok") -> str:
    return f'<span class="ecoscan-badge ecoscan-badge-{tone}">{html.escape(label)}</span>'


def _render_user_error(st: Any, exc: BaseException, *, context: str) -> None:
    from ecoscan.errors import describe_exception
    error = describe_exception(exc)
    log_message = (
        "ui_handled_error context=%s code=%s category=%s error_type=%s"
        % (context, error.code, error.category, type(exc).__name__)
    )
    LOGGER.warning(log_message)

    st.error(f"{error.code} - {error.title}: {error.message}")
    st.info(f"Ação recomendada: {error.action}")


def _class_label(class_id: str, guidance_by_class: dict[str, DisposalGuidance]) -> str:
    guidance = guidance_by_class.get(class_id)
    if not guidance:
        return class_id
    return f"{guidance.display_name} ({class_id})"


def _status_item(label: str, value: str, detail: str, tone: str = "ok") -> str:
    tone = tone if tone in {"ok", "warn", "danger"} else "ok"
    return (
        f'<div class="ecoscan-status-item ecoscan-status-{tone}">'
        f"<span>{html.escape(label)}</span>"
        f"<strong>{html.escape(value)}</strong>"
        f"<small>{html.escape(detail)}</small>"
        "</div>"
    )


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


def _guidance_class_labels(guidance_by_class: dict[str, DisposalGuidance]) -> dict[str, str]:
    return {class_id: guidance.display_name for class_id, guidance in guidance_by_class.items()}


def _html_list(items: tuple[str, ...] | list[str], *, empty_text: str = "Não configurado.") -> str:
    clean_items = [str(item).strip() for item in items if str(item).strip()]
    if not clean_items:
        return f'<p class="ecoscan-muted">{html.escape(empty_text)}</p>'
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in clean_items) + "</ul>"


