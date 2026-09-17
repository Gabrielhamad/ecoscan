from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

from PIL import Image

from ecoscan.config import load_config
from ecoscan.services.dataset_split import split_dataset


class DatasetSplitTests(unittest.TestCase):
    def test_split_dataset_creates_expected_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "config"
            raw_dir = root / "data" / "raw"
            config_dir.mkdir(parents=True)
            for class_id in ["plastic", "metal"]:
                for index in range(4):
                    image_path = raw_dir / class_id / f"{index}.png"
                    image_path.parent.mkdir(parents=True, exist_ok=True)
                    Image.new("RGB", (80, 80), (index * 20, 80, 120)).save(image_path)

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
                    "train_data": "data/train",
                    "validation_data": "data/validation",
                    "test_data": "data/test",
                    "reports": "reports",
                    "logs": "logs",
                    "models": "models",
                    "processed_data": "data/processed"
                },
                "dataset_split": {"train": 0.5, "validation": 0.25, "test": 0.25},
            }
            config_path = config_dir / "settings.json"
            config_path.write_text(json.dumps(settings), encoding="utf-8")
            config = load_config(config_path)

            records = split_dataset(config, overwrite=True)

            self.assertEqual(len(records), 8)
            self.assertTrue((root / "data" / "train" / "plastic").exists())
            self.assertTrue((root / "reports" / "dataset_split" / "split_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
