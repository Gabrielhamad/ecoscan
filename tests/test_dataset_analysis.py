from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from ecoscan.services.dataset_analysis import analyze_dataset, write_dataset_report


class DatasetAnalysisTests(unittest.TestCase):
    def _make_image(self, path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", size, color).save(path)

    def test_analyze_dataset_counts_classes_and_invalid_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_image(root / "plastic" / "bottle.png", (80, 90), (20, 140, 200))
            self._make_image(root / "glass" / "jar.jpg", (120, 80), (180, 220, 230))
            (root / "plastic" / "broken.png").write_bytes(b"not an image")
            (root / "glass" / "notes.txt").write_text("not supported", encoding="utf-8")

            result = analyze_dataset(
                root,
                configured_classes=["plastic", "glass", "battery"],
                allowed_extensions=frozenset({".png", ".jpg", ".jpeg"}),
                min_image_size=(64, 64),
                min_images_per_class_warning=1,
                imbalance_ratio_warning=2.0,
            )

            self.assertEqual(result["total_valid_images"], 2)
            self.assertEqual(result["total_invalid_images"], 2)
            self.assertEqual(result["class_counts"]["plastic"], 1)
            self.assertIn("battery", result["missing_classes"])
            self.assertTrue(any("Classe configurada sem imagens" in issue for issue in result["potential_issues"]))

    def test_write_dataset_report_creates_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "dataset"
            reports = Path(tmp) / "reports"
            self._make_image(root / "metal" / "can.png", (90, 90), (120, 120, 125))

            result = analyze_dataset(
                root,
                configured_classes=["metal"],
                allowed_extensions=frozenset({".png"}),
                min_image_size=(64, 64),
                min_images_per_class_warning=1,
                imbalance_ratio_warning=2.0,
            )
            written = write_dataset_report(result, reports, sample_limit=4, seed=42)
            written_names = {path.name for path in written}

            self.assertIn("dataset_analysis.json", written_names)
            self.assertIn("class_distribution.csv", written_names)
            self.assertIn("resolution_distribution.csv", written_names)
            self.assertIn("invalid_images.csv", written_names)
            self.assertIn("potential_issues.txt", written_names)
            self.assertIn("random_examples.jpg", written_names)


if __name__ == "__main__":
    unittest.main()

