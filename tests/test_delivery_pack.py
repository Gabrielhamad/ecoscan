from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import json
from types import SimpleNamespace
from unittest.mock import patch

from ecoscan.config import load_config
from ecoscan.services.delivery_pack import build_delivery_pack, write_delivery_pack


class DeliveryPackTests(unittest.TestCase):
    def test_delivery_pack_contains_acceptance_and_decisions(self) -> None:
        pack = build_delivery_pack(load_config())

        self.assertGreaterEqual(pack.readiness_score, 0)
        self.assertIn("AC-08", {item.code for item in pack.acceptance})
        self.assertIn("DEC-03", {item.code for item in pack.decisions})
        self.assertGreater(len(pack.evidence), 10)

    def test_delivery_pack_writes_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_delivery_pack(load_config(), Path(temp_dir))

            self.assertTrue(paths["index"].exists())
            self.assertTrue(paths["evidence"].exists())
            self.assertTrue(paths["acceptance"].exists())
            self.assertTrue(paths["completion"].exists())
            self.assertIn("Pacote de entrega APS", paths["index"].read_text(encoding="utf-8"))
            self.assertIn("Checklist de conclusão", paths["completion"].read_text(encoding="utf-8"))

    def test_artifact_presence_does_not_approve_independent_model_gate(self) -> None:
        for present in (False, True):
            with self.subTest(artifact_present=present), patch(
                "ecoscan.services.delivery_pack.model_status",
                return_value=SimpleNamespace(
                    final_model_exists=present,
                    selected_kind="semantic_onnx_assisted" if present else "none",
                ),
            ):
                pack = build_delivery_pack(load_config())
                model_gate = next(item for item in pack.acceptance if item.code == "AC-10")
                self.assertEqual(model_gate.status, "pending")

    def test_exported_inventory_is_explicitly_not_release_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_delivery_pack(load_config(), Path(temp_dir))
            summary = json.loads(paths["summary"].read_text(encoding="utf-8"))
            self.assertEqual(summary["release_acceptance"], "not_approved")
            model_gate = next(item for item in summary["acceptance"] if item["code"] == "AC-10")
            self.assertEqual(model_gate["status"], "pending")
            self.assertIn("não aprova release", paths["index"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
