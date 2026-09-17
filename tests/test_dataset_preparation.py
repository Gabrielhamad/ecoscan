from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from ecoscan.config import load_config
from ecoscan.services.dataset_preparation import prepare_dataset_images


class DatasetPreparationTests(unittest.TestCase):
    def test_prepare_dataset_images_writes_processed_images_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "raw"
            output_dir = tmp_path / "processed"
            report_dir = tmp_path / "reports"
            class_dir = source_dir / "plastic"
            class_dir.mkdir(parents=True)
            image_path = class_dir / "sample.png"
            image = Image.new("RGB", (160, 160), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((35, 30, 125, 135), fill=(210, 35, 35))
            image.save(image_path)

            summary, records = prepare_dataset_images(
                load_config(),
                source_dir=source_dir,
                output_dir=output_dir,
                report_dir=report_dir,
                overwrite=True,
                min_quality_score=0,
            )

            self.assertEqual(1, summary.total_seen)
            self.assertEqual(1, summary.prepared)
            self.assertEqual("prepared", records[0].status)
            self.assertTrue((output_dir / "plastic" / "sample_processed.png").exists())
            self.assertTrue((report_dir / "preparation_manifest.csv").exists())
            self.assertTrue((report_dir / "preparation_summary.md").exists())


if __name__ == "__main__":
    unittest.main()
