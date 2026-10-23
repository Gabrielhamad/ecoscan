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


def embedded_theme_css(preference="Automático"):
    """Components have their own document; explicitly carry the chosen palette."""
    if preference not in {"Automático", "Claro", "Escuro"}:
        raise ValueError('Unsupported appearance preference')
    palette = ':root {' + LIGHT + '} @media(prefers-color-scheme:dark) {:root {' + DARK + '}}'
    if preference != 'Automático':
        palette += ':root {' + (DARK if preference == 'Escuro' else LIGHT) + '}'
    return '<style>' + palette + '''
body {margin:0; background:transparent; color:var(--eco-ink); font:16px/1.5 system-ui,sans-serif;}
.eco-embedded {background:var(--eco-surface) !important; color:var(--eco-ink) !important;
  border-color:var(--eco-control-line) !important; box-shadow:none !important; padding:8px;}
.eco-embedded button, .eco-embedded a {
  box-sizing:border-box; background:var(--eco-primary) !important; color:var(--eco-on-primary) !important;
  border-color:var(--eco-primary) !important; min-height:48px !important; font-size:16px;
  padding:10px; box-shadow:none !important; overflow-wrap:anywhere;
}
.eco-embedded a small {color:inherit !important; font-size:14px !important; line-height:1.5;}
.eco-embedded [role="status"], #ecoscan_live_hint {
  color:var(--eco-muted) !important; font-size:14px !important; line-height:1.5; overflow-wrap:anywhere;
}
.eco-embedded a[aria-disabled="true"] {
  background:var(--eco-surface-soft) !important; color:var(--eco-muted) !important;
  border:1px dashed var(--eco-control-line) !important; cursor:not-allowed;
}
.eco-embedded a:focus-visible, .eco-embedded button:focus-visible {
  outline:3px solid var(--eco-water); outline-offset:2px;
}
</style>'''


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
