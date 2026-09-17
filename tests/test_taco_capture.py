from __future__ import annotations

import unittest

from scripts.capture_taco_dataset import _category_to_class, _is_large_enough, _scaled_crop_box


class TacoCaptureTests(unittest.TestCase):
    def test_category_map_points_taco_categories_to_ecoscan_classes(self) -> None:
        source_config = {
            "classes": {
                "medicine": ["Aluminium blister pack", "Carded blister pack"],
                "aerosol": ["Aerosol"],
            }
        }

        mapped = _category_to_class(source_config)

        self.assertEqual(mapped["Aluminium blister pack"], "medicine")
        self.assertEqual(mapped["Aerosol"], "aerosol")

    def test_scaled_crop_box_respects_actual_download_size_and_margin(self) -> None:
        box = _scaled_crop_box(
            [100.0, 50.0, 200.0, 100.0],
            source_width=1000,
            source_height=500,
            actual_width=500,
            actual_height=250,
            margin_ratio=0.10,
        )

        self.assertEqual(box, (40, 20, 160, 80))
        self.assertTrue(_is_large_enough(box, 32))

    def test_scaled_crop_box_clamps_to_image_bounds(self) -> None:
        box = _scaled_crop_box(
            [0.0, 0.0, 100.0, 100.0],
            source_width=100,
            source_height=100,
            actual_width=50,
            actual_height=50,
            margin_ratio=0.25,
        )

        self.assertEqual(box, (0, 0, 50, 50))


if __name__ == "__main__":
    unittest.main()
