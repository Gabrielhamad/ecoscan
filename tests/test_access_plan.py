from __future__ import annotations

import unittest

from ecoscan.services.access_plan import access_link_rows, build_access_plan, shareable_access_text


class AccessPlanTests(unittest.TestCase):
    def test_builds_local_and_network_links(self) -> None:
        plan = build_access_plan(lan_ip="192.168.0.50", streamlit_port=8501, live_port=8765)
        rows = access_link_rows(plan)

        self.assertEqual("192.168.0.50", plan.lan_ip)
        self.assertEqual("http://localhost:8501/?profile=usuario_demo", plan.local_links[0].url)
        self.assertEqual("http://192.168.0.50:8501/?profile=usuario_demo", plan.network_links[0].url)
        self.assertEqual("http://192.168.0.50:8765/", plan.network_links[2].url)
        self.assertEqual(6, len(rows))

    def test_share_text_guides_group_testing(self) -> None:
        plan = build_access_plan(lan_ip="10.0.0.8")
        text = shareable_access_text(plan)

        self.assertIn("EcoScan - links para teste", text)
        self.assertIn("http://10.0.0.8:8501/?profile=usuario_demo", text)
        self.assertIn("HTTPS", text)
        self.assertIn("corrigido", text)


if __name__ == "__main__":
    unittest.main()
