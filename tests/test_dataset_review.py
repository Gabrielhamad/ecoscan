from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from ecoscan.config import load_config
from ecoscan.services.dataset_review import apply_review_sheet, create_review_sheet


class DatasetReviewTests(unittest.TestCase):
    def test_create_and_apply_review_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "config"
            config_dir.mkdir()
            raw_dir = root / "data" / "raw"
            image_path = raw_dir / "plastic" / "item.png"
            image_path.parent.mkdir(parents=True)
            Image.new("RGB", (80, 80), "white").save(image_path)

            settings = {
                "project_name": "EcoScan",
                "classes": ["plastic", "metal"],
                "allowed_extensions": [".png"],
                "image_size": [224, 224],
                "confidence_threshold": 0.65,
                "random_seed": 42,
                "min_image_size": [64, 64],
                "min_images_per_class_warning": 1,
                "imbalance_ratio_warning": 2.0,
                "directories": {
                    "raw_data": "data/raw",
                    "curated_data": "data/curated",
                    "train_data": "data/train",
                    "validation_data": "data/validation",
                    "test_data": "data/test",
                    "reports": "reports",
                    "logs": "logs",
                    "models": "models",
                    "processed_data": "data/processed"
                },
            }
            config_path = config_dir / "settings.json"
            config_path.write_text(json.dumps(settings), encoding="utf-8")
            config = load_config(config_path)

            review_path = create_review_sheet(config)
            with review_path.open("r", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            rows[0]["suggested_class"] = "metal"
            with review_path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

            counts = apply_review_sheet(config, review_path=review_path, overwrite=True)

            self.assertEqual(counts["accepted"], 1)
            self.assertEqual(counts["reclassified"], 1)
            self.assertTrue((root / "data" / "curated" / "metal" / "item.png").exists())


if __name__ == "__main__":
    unittest.main()
