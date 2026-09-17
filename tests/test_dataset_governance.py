from __future__ import annotations

import unittest

from ecoscan.config import load_config
from ecoscan.services.dataset_governance import build_dataset_readiness, write_dataset_readiness_report


class DatasetGovernanceTests(unittest.TestCase):
    def test_dataset_readiness_reports_missing_images(self) -> None:
        summary, rows = build_dataset_readiness(load_config(), target_per_class=50)

        self.assertEqual(summary.target_per_class, 50)
        self.assertEqual(summary.class_count, len(rows))
        self.assertGreaterEqual(summary.missing_raw_total, 0)
        self.assertTrue(all(row.target_per_class == 50 for row in rows))

    def test_dataset_readiness_marks_special_waste(self) -> None:
        _, rows = build_dataset_readiness(load_config(), target_per_class=50)
        special_ids = {row.class_id for row in rows if row.is_special_waste}

        self.assertIn("battery", special_ids)
        self.assertIn("electronic", special_ids)

    def test_dataset_readiness_report_is_written(self) -> None:
        config = load_config()
        written = write_dataset_readiness_report(config, target_per_class=50)

        self.assertTrue(written["csv"].exists())
        self.assertTrue(written["json"].exists())
        self.assertTrue(written["markdown"].exists())


if __name__ == "__main__":
    unittest.main()
