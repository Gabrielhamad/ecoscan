"""Show startup feedback before loading the application's feature modules."""
import logging


def main():
    import streamlit as st

    st.set_page_config(page_title="Recicla SP", layout="wide", initial_sidebar_state="collapsed")
    loading = st.empty()
    loading.caption("Abrindo Recicla SP…")
    try:
        from ecoscan.ui.streamlit_app import main as render_app
    except (ImportError, OSError) as exc:
        # Provider or import exception messages may contain private paths/data.
        logging.getLogger(__name__).error("startup_import_failed type=%s", type(exc).__name__)
        loading.empty()
        st.error("Não foi possível iniciar o aplicativo. A instalação precisa ser verificada pelo responsável.")
        if st.button("Tentar abrir novamente", key="retry_startup"):
            st.rerun()
        return
    loading.empty()
    render_app(page_configured=True)
