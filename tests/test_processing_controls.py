from streamlit.testing.v1 import AppTest


def _app(filter_name="auto", segmentation="auto"):
    return AppTest.from_string(f'''
import streamlit as st
from ecoscan.config import load_config
from ecoscan.ui.processing_controls import select_filter_parameters, select_segmentation_parameters
st.json(select_filter_parameters(st, {filter_name!r}, load_config()))
st.json(select_segmentation_parameters(st, {segmentation!r}))
''').run()


def test_default_controls_do_not_add_parameters():
    app = _app()
    assert not app.exception
    assert [element.value for element in app.json] == ["{}", "{}"]


def test_otsu_and_canny_parameters_remain_available():
    app = _app("canny", "otsu")
    assert not app.exception
    assert len(app.slider) == 2
    assert len(app.radio) == 1
    app.radio[0].set_value("objeto escuro").run()
    assert '"invert": true' in app.json[1].value.lower()
