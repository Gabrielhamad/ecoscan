"""Export reviewed object annotations as oriented RGB images and COCO metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PIL import Image

from ecoscan.config import load_config
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.training.object_annotations import coco_annotations, load_object_annotations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--export-coco", choices=("train", "validation", "test"), required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new output directory.")

    config = load_config()
    payload = load_object_annotations(args.annotations, args.source_root, config.classes)
    exported = coco_annotations(payload, args.export_coco, config.classes)
    args.output.mkdir(parents=True)
    (args.output / "images").mkdir()
    selected = [image for image in payload["images"] if image["split"] == args.export_coco]
    for exported_image, original in zip(exported["images"], selected, strict=True):
        rgb = load_rgb_image(
            args.source_root / original["file_name"],
            allowed_extensions=config.allowed_extensions,
            min_size=config.min_image_size,
        ).array
        relative = f"images/{exported_image['id']:06d}.png"
        Image.fromarray(rgb).save(args.output / relative)
        exported_image["file_name"] = relative
        exported_image["source_sha256"] = original["sha256"]
    (args.output / "instances.json").write_text(
        json.dumps(exported, indent=2),
        encoding="utf-8",
    )
    print("COCO bounding boxes exported with EXIF-oriented, RGB PNG images.")


if __name__ == "__main__":
    main()
