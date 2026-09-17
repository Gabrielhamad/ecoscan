from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ecoscan.services.field_testing import (
    append_field_test_record,
    build_field_test_record,
    field_test_class_rows,
    field_test_rows,
    read_field_test_records,
    summarize_field_tests,
)


class FieldTestingTests(unittest.TestCase):
    def test_records_and_summarizes_field_tests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "field_tests.csv"
            append_field_test_record(
                path,
                build_field_test_record(
                    tester_id="usuario_demo",
                    tester_name="Cidadão",
                    expected_class="metal",
                    model_class="glass",
                    result_status="errou",
                    device_kind="celular",
                    capture_mode="foto enviada",
                    confidence=0.54,
                    note="lata virou vidro",
                ),
            )
            append_field_test_record(
                path,
                build_field_test_record(
                    tester_id="usuario_demo",
                    tester_name="Cidadão",
                    expected_class="plastic",
                    model_class="plastic",
                    result_status="acertou",
                    device_kind="computador",
                    capture_mode="upload",
                ),
            )

            records = read_field_test_records(path)
            summary = summarize_field_tests(records)
            rows = field_test_rows(records, {"metal": "Metal", "glass": "Vidro", "plastic": "Plástico"})
            class_rows = field_test_class_rows(records, {"metal": "Metal", "plastic": "Plástico"})

        self.assertEqual(2, summary.total)
        self.assertEqual(1, summary.wrong_count)
        self.assertEqual(1, summary.mobile_count)
        self.assertEqual("Vidro", rows[-1]["modelo"])
        self.assertEqual("Metal", class_rows[0]["classe"])
        self.assertEqual("média", class_rows[0]["prioridade"])

    def test_rejects_invalid_status(self) -> None:
        with self.assertRaises(ValueError):
            build_field_test_record(
                tester_id="u",
                tester_name="Usuário",
                expected_class="metal",
                result_status="talvez",
                device_kind="celular",
                capture_mode="foto",
            )


if __name__ == "__main__":
    unittest.main()
