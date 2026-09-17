from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ecoscan.services.civic_reports import (
    append_civic_report,
    append_civic_report_review,
    build_civic_report_review,
    build_civic_report_record,
    classify_report_verification,
    latest_reviews_by_report,
    read_civic_reports,
    read_civic_report_reviews,
)


class CivicReportTests(unittest.TestCase):
    def test_classify_report_consistent_when_analysis_is_accepted(self) -> None:
        result = SimpleNamespace(
            accepted=True,
            pipeline=SimpleNamespace(
                metadata={"capture_quality": {"status": "good"}},
                element_analysis=SimpleNamespace(significant_count=1),
            ),
        )

        status, note = classify_report_verification(result)

        self.assertEqual(status, "triagem_consistente")
        self.assertIn("reconhecimento", note)

    def test_classify_report_recommends_new_image_when_quality_is_bad(self) -> None:
        result = SimpleNamespace(
            accepted=True,
            pipeline=SimpleNamespace(
                metadata={"capture_quality": {"status": "retake"}},
                element_analysis=SimpleNamespace(significant_count=0),
            ),
        )

        status, _ = classify_report_verification(result)

        self.assertEqual(status, "imagem_insuficiente")

    def test_append_and_read_civic_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_path = Path(tmp) / "evidence.jpg"
            evidence_path.write_bytes(b"image-bytes")
            result = SimpleNamespace(
                accepted=True,
                predicted_class="plastic",
                top_class="plastic",
                probability=0.81,
                pipeline=SimpleNamespace(
                    metadata={
                        "filter": {"name": "auto", "decision": {"selected": "clahe"}},
                        "segmentation": {"name": "auto", "decision": {"selected": "grabcut"}},
                        "capture_quality": {"status": "good", "score": 89},
                    },
                    element_analysis=SimpleNamespace(significant_count=2),
                ),
            )
            record = build_civic_report_record(
                result,
                evidence_path=evidence_path,
                location_note="Praça central",
                description="Descarte em área pública",
                submitted_by="usuario_demo",
            )
            manifest = Path(tmp) / "reports.csv"

            append_civic_report(manifest, record)
            rows = read_civic_reports(manifest)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].detected_class, "plastic")
            self.assertEqual(rows[0].verification_status, "triagem_consistente")
            self.assertEqual(rows[0].capture_quality_score, 89)
            self.assertEqual(rows[0].submitted_by, "usuario_demo")

    def test_append_and_read_civic_report_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "reviews.csv"
            review = build_civic_report_review(
                report_id="report-1",
                admin_user_id="admin_secretaria",
                decision="encaminhar",
                note="Enviar para fiscalização.",
            )

            append_civic_report_review(manifest, review)
            rows = read_civic_report_reviews(manifest)
            latest = latest_reviews_by_report(rows)

            self.assertEqual(rows[0].decision, "encaminhar")
            self.assertEqual(latest["report-1"].note, "Enviar para fiscalização.")


if __name__ == "__main__":
    unittest.main()
