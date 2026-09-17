from __future__ import annotations

import unittest

from ecoscan.config import load_config
from ecoscan.services.deployment_readiness import (
    build_free_hosting_plan,
    deployment_check_rows,
    format_free_hosting_markdown,
)


class DeploymentReadinessTests(unittest.TestCase):
    def test_free_hosting_plan_exposes_streamlit_cloud_path(self) -> None:
        plan = build_free_hosting_plan(load_config())
        rows = deployment_check_rows(plan.checks)
        markdown = format_free_hosting_markdown(plan)

        self.assertEqual("Streamlit Community Cloud", plan.recommended_platform)
        self.assertEqual("streamlit_app.py", plan.entrypoint)
        self.assertTrue(plan.can_use_camera_photo)
        self.assertFalse(plan.live_mode_available)
        self.assertTrue(any(row["item"] == "Entrada Streamlit na raiz" for row in rows))
        self.assertIn("Hospedagem gratuita", markdown)
        self.assertIn("EcoScan Live separado", markdown)


if __name__ == "__main__":
    unittest.main()
