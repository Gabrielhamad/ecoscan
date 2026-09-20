import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from ecoscan.config import PROJECT_ROOT
from ecoscan.ui.education import LESSONS


class EducationTests(unittest.TestCase):
    def test_material_assets_and_sources(self):
        self.assertEqual(set(LESSONS), {'plastic', 'metal', 'paper_cardboard', 'glass', 'battery', 'electronic'})
        for lesson in LESSONS.values():
            self.assertTrue((PROJECT_ROOT / 'assets' / 'disposal_targets' / lesson[1]).is_file())
            self.assertTrue(lesson[-1].startswith('https://'))

    def test_all_material_views_render(self):
        app = AppTest.from_string('from ecoscan.ui.education import render_education\nfrom ecoscan.config import PROJECT_ROOT\nimport streamlit as st\nrender_education(st, PROJECT_ROOT)').run()
        for key in LESSONS:
            app.selectbox[0].set_value(key).run()
            self.assertEqual(len(app.exception), 0)

    def test_email_preserves_provider_confirmation_link(self):
        template = (PROJECT_ROOT / 'templates' / 'confirm_signup_pt.html').read_text(encoding='utf-8')
        self.assertIn('{{ .ConfirmationURL }}', template)
        self.assertIn('lang="pt-BR"', template)
        self.assertNotIn('<script', template)
