from streamlit.testing.v1 import AppTest


def test_map_default_and_invalid_postcode():
    app = AppTest.from_string('''
import streamlit as st
from ecoscan.ui.collection_map import render_collection_map
from ecoscan.disposal.collection_points import load_collection_points
from ecoscan.disposal.guidance import load_guidance
from ecoscan.config import PROJECT_ROOT
render_collection_map(st, load_collection_points(PROJECT_ROOT / "config/collection_points.json"), load_guidance(PROJECT_ROOT / "config/disposal_guidance.json"))
''').run()
    assert not app.exception
    assert len(app.expander) == 22
    app.selectbox(key="collection_region").set_value("Norte").run()
    assert len(app.expander) == 4
    app.selectbox(key="collection_material").set_value("battery").run()
    assert len(app.expander) == 0
    assert app.info
    app.text_input[0].set_value("123").run()
    app.button[0].click().run()
    assert not app.exception
    assert any("8 números" in item.value for item in app.error)


def test_rewards_unlock_without_monetary_claims():
    source = '''
import streamlit as st
from types import SimpleNamespace
from ecoscan.ui.rewards import render_rewards
from ecoscan.services.campaigns import load_campaign
from ecoscan.config import PROJECT_ROOT
render_rewards(st, load_campaign(PROJECT_ROOT / "config/campaigns.json"), POINTS, SimpleNamespace(id="USER", display_name="Teste <script>"))
'''
    app = AppTest.from_string(source.replace("POINTS", "0").replace('id="USER"', 'id="visitor_a"')).run()
    assert not app.exception
    assert len(app.get("download_button")) == 0
    app = AppTest.from_string(source.replace("POINTS", "220")).run()
    assert not app.exception
    assert len(app.get("download_button")) == 3
