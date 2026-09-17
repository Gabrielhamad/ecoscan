from __future__ import annotations

import unittest

from ecoscan.config import load_config
from ecoscan.services.dataset_reliability import assess_class_reliability


class DatasetReliabilityTests(unittest.TestCase):
    def test_assess_class_reliability_returns_status_for_active_class(self) -> None:
        reliability = assess_class_reliability(load_config(), "battery")

        self.assertIsNotNone(reliability)
        assert reliability is not None
        self.assertEqual("battery", reliability.class_id)
        self.assertIn(reliability.status, {"sufficient", "limited", "scarce"})
        self.assertGreaterEqual(reliability.raw_count, 0)


if __name__ == "__main__":
    unittest.main()
