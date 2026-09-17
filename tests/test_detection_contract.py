from __future__ import annotations

import unittest

from ecoscan.detection.contracts import MultipleObjectDetectionNotEnabled, detect_multiple_objects


class DetectionContractTests(unittest.TestCase):
    def test_multiple_object_detection_is_explicitly_future_feature(self) -> None:
        with self.assertRaises(MultipleObjectDetectionNotEnabled):
            detect_multiple_objects()


if __name__ == "__main__":
    unittest.main()

