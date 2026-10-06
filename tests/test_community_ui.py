import copy
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest


class CommunityUITests(unittest.TestCase):
    def setUp(self):
        self.store = MagicMock()
        self.row = {"id": "c6a4f3f0-5d12-4e2d-b8b2-b4f3f7c08de8", "revision": 0,
                    "created_at": "2026-10-05T12:00:00Z", "reviews": [],
                    "record": {"location_note": "Bairro de teste", "description": "Relato educativo"}}
        self.store.reports.return_value = [copy.deepcopy(self.row)]
        patch("ecoscan.ui.community.community_store", return_value=self.store).start()
        patch("ecoscan.ui.community.community_enabled", return_value=True).start()
        patch("ecoscan.ui.community.credentials", return_value={"token": "test", "access": {}}).start()
        self.addCleanup(patch.stopall)

    def reports(self, admin=False):
        return AppTest.from_string(f'''
import streamlit as st
from ecoscan.ui.community import render_reports
render_reports(st, admin={admin!r})
''').run()

    def test_citizen_sees_response_without_admin_controls(self):
        self.store.reports.return_value[0]["reviews"] = [{"decision": "arquivar", "note": "Resposta de teste"}]
        app = self.reports()
        self.assertFalse(app.exception)
        self.assertTrue(any("Resposta de teste" in text.value for text in app.markdown))
        self.assertFalse(any(button.label == "Registrar resposta" for button in app.button))
        self.store.reports.assert_called_with(token="test", access={}, own_only=True, limit=100)

    def test_unavailable_is_not_empty_history(self):
        self.store.reports.side_effect = OSError("Banco indisponível")
        app = self.reports()
        self.assertFalse(app.exception)
        self.assertEqual(app.error[0].value, "Banco indisponível")
        self.assertFalse(app.info)

    def test_admin_keeps_original_revision_during_rerun(self):
        app = self.reports(admin=True)
        self.store.reports.return_value[0]["revision"] = 1
        self.store.review.side_effect = ValueError("Outro analista revisou")
        app.text_area[0].set_value("Resposta")
        next(b for b in app.button if b.label == "Registrar resposta").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(self.store.review.call_args.kwargs["expected_revision"], 0)
        self.assertTrue(app.error)
        self.assertFalse(app.success)

    def test_disabled_does_not_connect(self):
        with patch("ecoscan.ui.community.community_enabled", return_value=False):
            app = self.reports()
        self.assertFalse(app.exception)
        self.store.reports.assert_not_called()

    def test_campaign_draft_keeps_revision_on_publish(self):
        root = Path(__file__).parents[1]
        payload = json.loads((root / "config/campaigns.json").read_text(encoding="utf-8"))
        self.store.campaign.return_value = {"record": payload, "revision": 0}
        app = AppTest.from_string(f'''
import streamlit as st
from pathlib import Path
from types import SimpleNamespace
from ecoscan.ui.community import render_campaign_editor
render_campaign_editor(st, SimpleNamespace(project_root=Path({str(root)!r})))
''').run()
        self.assertFalse(app.exception)
        self.store.campaign.return_value["revision"] = 1
        self.store.publish_campaign.side_effect = ValueError("A campanha mudou")
        app.text_input[0].set_value("Novo título")
        next(b for b in app.button if b.label == "Publicar para todos").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(self.store.publish_campaign.call_args.kwargs["expected_revision"], 0)
        self.assertTrue(app.error)
        self.assertFalse(app.success)
