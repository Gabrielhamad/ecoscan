import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class ReceiptUITests(unittest.TestCase):
    def app(self):
        return AppTest.from_string('''
import streamlit as st
import numpy as np
from types import SimpleNamespace
from ecoscan.ui.learning import render_contribution
result = SimpleNamespace(accepted=True, pipeline=SimpleNamespace(
    loaded=SimpleNamespace(array=np.zeros((8,8,3), dtype=np.uint8))))
render_contribution(st, None, result, SimpleNamespace(id="supabase_test"))
''', default_timeout=20)

    def test_saved_receipt_survives_failed_photo_export(self):
        record = {"id": "93c177b8-7bff-426a-87df-2ec8c4b459cf", "item_id": "drink_can",
                  "status": "pending", "storage_key": "photo.jpg"}
        with patch("ecoscan.ui.learning.submit_contribution", return_value=record) as submit, \
             patch("ecoscan.ui.learning.contribution_package", side_effect=OSError("offline")) as export:
            app = self.app().run()
            app.selectbox[0].select("drink_can")
            app.checkbox[0].check()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.success)
            export.assert_not_called()
            next(b for b in app.button if b.label == "Preparar cópia com foto").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.success)
            self.assertTrue(app.warning)
            self.assertEqual(submit.call_count, 1)

    def test_write_failure_has_no_success_receipt(self):
        with patch("ecoscan.ui.learning.submit_contribution", side_effect=OSError("offline")):
            app = self.app().run()
            app.selectbox[0].select("drink_can")
            app.checkbox[0].check()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.success)
            self.assertIn("Atualizar protocolos", app.error[0].value)

    def test_own_protocols_render_on_mobile_without_wide_table(self):
        row = {"id": "93c177b8-7bff-426a-87df-2ec8c4b459cf", "item_id": "drink_can",
               "status": "approved", "response": "Confirmamos uma lata.", "training_status": "queued"}
        with patch("ecoscan.ui.learning.citizen_contributions", return_value=[row]), \
             patch("ecoscan.ui.learning.persistent_enabled", return_value=True):
            app = AppTest.from_string('''
import streamlit as st
from types import SimpleNamespace
from ecoscan.ui.learning import render_citizen_protocols
render_citizen_protocols(st, None, SimpleNamespace(id="supabase_test"))
''').run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.dataframe), 0)
            self.assertTrue(any("Confirmamos uma lata" in m.value for m in app.markdown))
            self.assertTrue(any("vinculados" in m.value for m in app.caption))


if __name__ == "__main__":
    unittest.main()
