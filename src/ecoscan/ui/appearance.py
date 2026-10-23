"""Shared, accessible presentation for the citizen and secretariat workspaces."""
from pathlib import Path


def render_theme(st):
    with st.popover("Aparência", icon=":material/contrast:"):
        preference = st.radio("Tema", ["Automático", "Claro", "Escuro"],
                              horizontal=True, key="recicla_sp_appearance")
    st.markdown("<style>" + theme_css(preference) + "</style>", unsafe_allow_html=True)


def theme_css(preference="Automático"):
    if preference not in {"Automático", "Claro", "Escuro"}:
        raise ValueError('Unsupported appearance preference')
    css = Path(__file__).with_name("appearance.css").read_text(encoding="utf-8")
    css += '\n:root {' + LIGHT + '}\n@media(prefers-color-scheme:dark) {:root {' + DARK + '}}'
    # Explicit choice overrides the OS preference without modifying account data.
    if preference != "Automático":
        palette = DARK if preference == "Escuro" else LIGHT
        css += "\n:root {" + palette + "}"
    return css


LIGHT = """
--eco-bg:#f5f8f7; --eco-surface:#ffffff; --eco-surface-soft:#eaf1ee;
--eco-ink:#182b27; --eco-ink-strong:#102c24; --eco-muted:#50665e;
--eco-line:#c6d5ce; --eco-primary:#086647; --eco-primary-soft:#def2e7;
--eco-control-line:#71877c;
--eco-water:#08717c; --eco-blue:#175f9d; --eco-blue-soft:#e4eff9;
--eco-accent:#865c04; --eco-danger:#aa302f; --eco-on-primary:#ffffff;
color-scheme:light;
"""
DARK = """
--eco-bg:#101715; --eco-surface:#19231f; --eco-surface-soft:#23332c;
--eco-ink:#eaf3ed; --eco-ink-strong:#ffffff; --eco-muted:#b4c8bc;
--eco-line:#455d50; --eco-primary:#87edb8; --eco-primary-soft:#203f30;
--eco-control-line:#8ba497;
--eco-water:#7adce4; --eco-blue:#a2cfff; --eco-blue-soft:#243a49;
--eco-accent:#f0ce76; --eco-danger:#ffb4ae; --eco-on-primary:#09291b;
color-scheme:dark;
"""
