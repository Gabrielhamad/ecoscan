"""Shared Recicla SP identity for both workspaces."""


def render_citizen_design(st, image_uri, *, admin=False):
    context = "Secretaria · gestão ambiental" if admin else "São Paulo · educação ambiental"
    subtitle = "Campanhas, participação e cuidado com a cidade." if admin else "Um novo destino para o que você descarta."
    st.markdown(f'''<section class="recicla-header">
      <div class="recicla-mark" aria-hidden="true">&#9851;</div>
      <div><div class="recicla-eyebrow">{context}</div>
      <h1>Recicla <span>SP</span></h1><p>{subtitle}</p></div>
    </section>''', unsafe_allow_html=True)
