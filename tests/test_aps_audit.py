from __future__ import annotations

import unittest

from ecoscan.config import load_config
from ecoscan.services.aps_audit import build_aps_audit, format_audit_markdown, summarize_audit


class ApsAuditTests(unittest.TestCase):
    def test_audit_contains_manual_gates(self) -> None:
        items = build_aps_audit(load_config())
        codes = {item.code for item in items}

        self.assertIn("APS-PROC-01", codes)
        self.assertIn("APS-SEG-01", codes)
        self.assertIn("APS-DATA-00", codes)
        self.assertIn("APS-MODEL-03", codes)

    def test_summary_has_readiness_score(self) -> None:
        summary = summarize_audit(build_aps_audit(load_config()))

        self.assertIn("readiness_score", summary)
        self.assertGreater(summary["total_items"], 5)

    def test_markdown_mentions_attention_items(self) -> None:
        markdown = format_audit_markdown(build_aps_audit(load_config()))

        self.assertIn("Auditoria de engenharia do EcoScan", markdown)
        self.assertIn("Atenções de alta prioridade", markdown)


if __name__ == "__main__":
    unittest.main()
