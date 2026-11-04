"""Streamlit controls that describe processing without importing image engines."""
from typing import Any


FILTERS = ("auto", "none", "gaussian", "median", "clahe", "sobel", "canny", "bilateral")
SEGMENTATIONS = ("auto", "none", "otsu", "hsv_color", "grabcut")


def select_filter_parameters(st: Any, filter_name: str, config=None) -> dict[str, Any]:
    if filter_name == "auto":
        st.caption("Correções condicionais por ruído e faixa tonal, com limites para preservar cor e contornos.")
        return {}
    if filter_name == "gaussian":
        return {
            "kernel_size": st.select_slider("Kernel Gaussiano", options=[3, 5, 7, 9], value=5),
            "sigma": st.slider("Sigma", 0.1, 5.0, 1.0, 0.1),
        }
    if filter_name == "median":
        value = config.filters.get("median", {}).get("kernel_size", 3) if config else 3
        return {"kernel_size": st.select_slider(
            "Kernel mediana", options=[3, 5, 7, 9], value=value,
        )}
    if filter_name == "bilateral":
        return {
            "diameter": st.select_slider("Diâmetro bilateral", options=[5, 7, 9, 11], value=9),
            "sigma_color": st.slider("Sigma cor", 10, 150, 75, 5),
            "sigma_space": st.slider("Sigma espaço", 10, 150, 75, 5),
        }
    if filter_name == "clahe":
        return {
            "clip_limit": st.slider("Clip limit", 0.5, 6.0, 2.0, 0.1),
            "tile_grid_size": [
                st.select_slider("Grade CLAHE horizontal", options=[4, 8, 12, 16], value=8),
                st.select_slider("Grade CLAHE vertical", options=[4, 8, 12, 16], value=8),
            ],
        }
    if filter_name == "canny":
        low = st.slider("Canny baixo", 10, 240, 80, 5)
        high = st.slider("Canny alto", low + 5, 255, max(160, low + 5), 5)
        return {"threshold1": low, "threshold2": high}
    return {}


def select_segmentation_parameters(st: Any, segmentation_name: str) -> dict[str, Any]:
    if segmentation_name == "auto":
        st.caption("Máscara auxiliar por Otsu ou GrabCut. Se a separação falhar, a foto completa é preservada.")
        return {}
    if segmentation_name == "otsu":
        mode = st.radio("Máscara Otsu", ["automática", "objeto claro", "objeto escuro"], horizontal=True)
        return {"invert": {"objeto claro": False, "objeto escuro": True}.get(mode)}
    if segmentation_name == "hsv_color":
        return {
            "saturation_min": st.slider("Saturação mínima", 0, 255, 45, 5),
            "value_min": st.slider("Brilho mínimo", 0, 255, 35, 5),
        }
    if segmentation_name == "grabcut":
        return {
            "iterations": st.slider("Iterações GrabCut", 1, 10, 5, 1),
            "margin_percent": st.slider("Margem central", 0.02, 0.25, 0.08, 0.01),
        }
    return {}
