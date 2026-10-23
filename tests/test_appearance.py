import re

import pytest
from streamlit.testing.v1 import AppTest

from ecoscan.ui.appearance import DARK, LIGHT, theme_css, embedded_theme_css


def luminance(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
    return sum(c * weight for c, weight in zip(linear, (.2126, .7152, .0722)))


@pytest.mark.parametrize("palette", [LIGHT, DARK])
def test_text_and_action_colors_meet_normal_text_contrast(palette):
    colors = dict(re.findall(r"(--eco-[\w-]+):(#[0-9a-f]{6})", palette))
    for foreground, background in [
        ("ink", "bg"), ("ink", "surface"), ("muted", "bg"),
        ("primary", "primary-soft"), ("on-primary", "primary"),
        ("blue", "surface"), ("accent", "bg"), ("danger", "surface"),
        ("muted", "surface-soft"), ("ink", "surface-soft"), ("blue", "bg"),
        ("water", "surface"), ("accent", "surface-soft"), ("danger", "surface-soft"),
    ]:
        a, b = sorted([luminance(colors["--eco-" + foreground]),
                       luminance(colors["--eco-" + background])])
        assert (b + .05) / (a + .05) >= 4.5, (foreground, background)


@pytest.mark.parametrize('palette', [LIGHT, DARK])
def test_control_boundaries_have_visible_contrast(palette):
    colors = dict(re.findall(r'(--eco-[\w-]+):(#[0-9a-f]{6})', palette))
    for surface in ('bg', 'surface'):
        high, low = sorted([luminance(colors['--eco-control-line']),
                            luminance(colors['--eco-' + surface])], reverse=True)
        assert (high + .05) / (low + .05) >= 3


def test_manual_theme_overrides_automatic_and_palette_has_single_source():
    assert theme_css('Claro').endswith(':root {' + LIGHT + '}')
    assert theme_css('Escuro').endswith(':root {' + DARK + '}')
    assert theme_css().count('--eco-bg:') == 2
    with pytest.raises(ValueError):
        theme_css('invalid')


@pytest.mark.parametrize('theme,palette', [('Claro', LIGHT), ('Escuro', DARK)])
def test_embedded_components_use_manual_palette_after_os_rule(theme, palette):
    css = embedded_theme_css(theme)
    assert css.rfind(':root {' + palette + '}') > css.index('@media')
    assert 'font-size:14px !important' in css
    assert 'aria-disabled' in css


def test_location_and_camera_components_receive_current_theme():
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch
    from ecoscan.ui.streamlit_app import _render_browser_location_search, _render_live_camera_link
    st = MagicMock()
    st.session_state = {'recicla_sp_appearance': 'Escuro'}
    with patch('streamlit.components.v1.html') as render:
        _render_browser_location_search(st, SimpleNamespace(class_id='plastic', search_query='reciclagem'))
        _render_live_camera_link(st)
    assert render.call_count == 2
    for call in render.call_args_list:
        assert embedded_theme_css('Escuro') in call.args[0]
        assert call.kwargs['scrolling'] is True
    assert 'role="status"' in render.call_args_list[0].args[0]


def test_appearance_switch_preserves_page_and_selection():
    app = AppTest.from_string('''
import streamlit as st
from ecoscan.ui.appearance import render_theme
from ecoscan.ui.citizen_design import render_citizen_design
render_theme(st)
render_citizen_design(st, "")
st.text_input("Nome", key="draft_name")
''').run()
    app.text_input[0].set_value("Participante").run()
    for theme in ("Escuro", "Claro", "Automático"):
        app.radio[0].set_value(theme).run()
        assert not app.exception
        assert app.text_input[0].value == "Participante"
        assert app.radio[0].value == theme


@pytest.mark.parametrize('admin', [True, False])
def test_shared_theme_renders_both_workspace_headers(admin):
    app = AppTest.from_string('''
import streamlit as st
from ecoscan.ui.appearance import render_theme
from ecoscan.ui.citizen_design import render_citizen_design
render_theme(st)
render_citizen_design(st, "", admin=''' + repr(admin) + ''')
st.button("Confirmar", type="primary")
st.text_input("Nome")
''').run()
    for theme in ('Claro', 'Escuro'):
        app.radio[0].set_value(theme).run()
        assert not app.exception
        assert any('Recicla' in item.value for item in app.markdown)
        assert app.button[0].label == 'Confirmar'
