import unittest

from streamlit.testing.v1 import AppTest


class ScopeGuidanceTests(unittest.TestCase):
    def test_assisted_disposal_is_separate_from_recognition(self):
        app = AppTest.from_string(
            "import streamlit as st\n"
            "from ecoscan.ui.learning import render_scope\n"
            "render_scope(st)\n", default_timeout=20,
        ).run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("Medicamentos vencidos ou sem uso: consultar descarte",
                      [entry.label for entry in app.expander])
        self.assertTrue(any("não identificamos remédios" in entry.value
                            for entry in app.markdown))
        self.assertTrue(any("perfurocortantes" in entry.value for entry in app.warning))


if __name__ == "__main__":
    unittest.main()
