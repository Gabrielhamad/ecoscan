"""Reproducible local visual audit; output images are not training data."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ecoscan.app.pipeline import run_processing_pipeline
from ecoscan.config import load_config
from ecoscan.image_processing.adaptive_filters import apply_adaptive_filter_pipeline


def audit_synthetic(output_dir, config):
    """Known clean reference separates denoising quality from input similarity."""
    from skimage.metrics import structural_similarity

    clean = np.full((160, 160, 3), (190, 200, 215), dtype=np.uint8)
    clean[30:130, 45:115] = (135, 55, 40)
    clean[30:36, 45:115] = (145, 150, 155)
    clean[124:130, 45:115] = (145, 150, 155)
    impulsive = clean.copy()
    impulsive[np.random.default_rng(42).random(clean.shape[:2]) < .015] = 255
    gaussian = np.clip(clean.astype(float) + np.random.default_rng(42).normal(0, 9, clean.shape), 0, 255).astype(np.uint8)
    rows = []
    for name, source in [("clean", clean), ("impulse", impulsive), ("gaussian", gaussian)]:
        result = apply_adaptive_filter_pipeline(source, config.filters)
        metrics = {}
        for stage, array in [("before", source), ("after", result.filter_result.image)]:
            mse = float(np.mean((array.astype(float) - clean) ** 2))
            metrics[stage] = {"mse": mse, "psnr_db": float(10 * np.log10(255 ** 2 / mse)) if mse else None,
                              "ssim_reference": float(structural_similarity(clean, array, channel_axis=-1, data_range=255))}
        rows.append({"case": name, "filter": result.decision["selected"], "metrics": metrics})
        canvas = Image.new("RGB", (480, 190), "white")
        draw = ImageDraw.Draw(canvas)
        for column, (label, array) in enumerate([("Reference", clean), ("Before", source), ("After", result.filter_result.image)]):
            draw.text((column * 160 + 5, 6), label, fill="black")
            canvas.paste(Image.fromarray(array), (column * 160, 30))
        canvas.save(output_dir / f"synthetic_{name}.png")
    (output_dir / "synthetic_metrics.json").write_text(json.dumps(rows, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(rows, indent=2, allow_nan=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--synthetic", action="store_true", help="Audit against a known reference, without training")
    parser.add_argument("images", nargs="*", type=Path)
    args = parser.parse_args()
    config = load_config()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.synthetic:
        if args.images:
            parser.error("--synthetic cannot be combined with image paths")
        audit_synthetic(args.output, config)
        return
    paths = args.images or [
        next(iter(sorted(p for p in (config.directories["curated_data"] / label).glob("*")
                         if p.suffix.lower() in config.allowed_extensions)), None)
        for label in config.classes
    ]
    rows = []
    for index, path in enumerate(p for p in paths if p and p.is_file()):
        start = time.perf_counter()
        result = run_processing_pipeline(path, config)
        output = result.model_input_preview
        row = {
            "case": index + 1,
            "latency_ms": round((time.perf_counter() - start) * 1000, 1),
            "input_shape": list(result.loaded.array.shape),
            "working_shape": list(result.preprocessing.resized.shape),
            "output_shape": list(output.shape),
            "filter": result.metadata["filter"]["decision"],
            "segmentation": result.metadata["segmentation"]["decision"],
            "mask_coverage": result.segmentation_result.foreground_ratio,
            "preparation": result.metadata.get("recognition_preparation", {"profile": "legacy_masked"}),
        }
        canvas = Image.new("RGB", (1200, 450), "white")
        draw = ImageDraw.Draw(canvas)
        for col, (label, array) in enumerate([
            ("Original", result.loaded.array), ("Prepared RGB", result.filter_result.image),
            ("Mask (diagnostic)", result.segmentation_result.mask), ("Classifier input", output),
        ]):
            image = Image.fromarray(array).convert("RGB")
            image.thumbnail((290, 400), Image.Resampling.LANCZOS)
            canvas.paste(image, (col * 300 + (300 - image.width) // 2, 35))
            draw.text((col * 300 + 10, 10), label, fill="black")
        canvas.save(args.output / f"case_{index + 1:02d}.png")
        rows.append(row)
        print(f"case {index + 1}: {row['filter']['selected']}, {row['segmentation']['selected']}", flush=True)
    (args.output / "audit.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
