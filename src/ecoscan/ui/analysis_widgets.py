"""Small widgets used by the photo analysis page.

The entry point and page controller may reuse these without circular imports.
"""
from __future__ import annotations

import html
import os
from typing import Any

from ecoscan.disposal.guidance import DisposalGuidance
from ecoscan.services.accounts import UserProfile
from ecoscan.services.recognition_safety import capture_photo_tips


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


