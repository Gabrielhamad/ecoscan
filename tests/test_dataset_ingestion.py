from __future__ import annotations

import csv
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image

from ecoscan.config import load_config
from ecoscan.services.dataset_ingestion import IncomingImage, ingest_uploaded_images


def _png_bytes(color: str = "white", size: tuple[int, int] = (80, 80)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _config(tmp: Path):
    config_dir = tmp / "config"
    config_dir.mkdir()
    settings = {
        "project_name": "EcoScan",
        "classes": ["plastic", "battery"],
        "allowed_extensions": [".png", ".jpg"],
        "image_size": [224, 224],
        "confidence_threshold": 0.65,
        "random_seed": 42,
        "min_image_size": [64, 64],
        "directories": {
            "raw_data": "data/raw",
            "curated_data": "data/curated",
            "processed_data": "data/processed",
            "train_data": "data/train",
            "validation_data": "data/validation",
            "test_data": "data/test",
            "models": "models",
            "reports": "reports",
            "logs": "logs",
        },
    }
    config_path = config_dir / "settings.json"
    config_path.write_text(json.dumps(settings), encoding="utf-8")
    return load_config(config_path)


class DatasetIngestionTests(unittest.TestCase):
    def test_valid_upload_goes_to_raw_dataset_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _config(root)
            manifest = root / "reports" / "uploads.csv"

            results = ingest_uploaded_images(
                config,
                "battery",
                [IncomingImage("Pilha AA.png", _png_bytes(), "unit-test")],
                manifest_path=manifest,
            )

            self.assertEqual(results[0].status, "saved")
            saved_path = config.project_root / results[0].saved_path
            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.parent.name, "battery")

            with manifest.open("r", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(rows[0]["status"], "saved")
            self.assertEqual(rows[0]["class_id"], "battery")

    def test_duplicate_upload_is_not_saved_twice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            payload = _png_bytes("red")

            first = ingest_uploaded_images(config, "plastic", [IncomingImage("item.png", payload)])
            second = ingest_uploaded_images(config, "battery", [IncomingImage("outro.png", payload)])

            self.assertEqual(first[0].status, "saved")
            self.assertEqual(second[0].status, "duplicate")
            self.assertTrue(second[0].duplicate_of.endswith(first[0].saved_path))
            files = list(config.directories["raw_data"].rglob("*.png"))
            self.assertEqual(len(files), 1)

    def test_invalid_extension_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))

            results = ingest_uploaded_images(
                config,
                "plastic",
                [IncomingImage("anotacao.txt", b"isso nao e uma imagem")],
            )

            self.assertEqual(results[0].status, "rejected")
            self.assertEqual(list(config.directories["raw_data"].rglob("*")), [])


if __name__ == "__main__":
    unittest.main()
