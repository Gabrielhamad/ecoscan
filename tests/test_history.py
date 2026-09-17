from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ecoscan.services.history import append_history_entry, build_history_entry, read_history


class HistoryTests(unittest.TestCase):
    def test_append_and_read_history_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.jsonl"
            result = SimpleNamespace(
                guidance=SimpleNamespace(environmental_category="Reciclável", guidance="Coleta seletiva"),
                pipeline=SimpleNamespace(
                    metadata={
                        "filter": {"name": "gaussian"},
                        "segmentation": {"name": "otsu"},
                        "capture_quality": {"status": "good", "score": 93},
                    }
                ),
                predicted_class="metal",
                top_class="metal",
                probability=0.91,
                accepted=True,
                model_type="knn_baseline",
            )

            entry = build_history_entry(result, source_path="sample.jpg")
            append_history_entry(path, entry)
            entries = read_history(path)

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].predicted_class, "metal")
            self.assertEqual(entries[0].source_path, "sample.jpg")
            self.assertEqual(entries[0].filter_decision, "gaussian")
            self.assertEqual(entries[0].segmentation_decision, "otsu")
            self.assertEqual(entries[0].capture_quality_status, "good")

    def test_read_history_ignores_unknown_future_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.jsonl"
            path.write_text(
                (
                    '{"id":"1","timestamp_utc":"2026-01-01T00:00:00Z","source_path":"a.jpg",'
                    '"predicted_class":"metal","top_class":"metal","probability":0.9,"accepted":true,'
                    '"model_type":"baseline","filter_name":"gaussian","segmentation_name":"otsu",'
                    '"environmental_category":"Reciclável","guidance_summary":"Coleta seletiva",'
                    '"future_field":"ok"}\n'
                ),
                encoding="utf-8",
            )

            entries = read_history(path)

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].filter_name, "gaussian")


if __name__ == "__main__":
    unittest.main()
