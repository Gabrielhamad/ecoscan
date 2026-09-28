"""Reproducible morphology experiment, runnable without Auth or a trained model."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
from ecoscan.app.pipeline import ProcessingPipelineOptions, run_processing_pipeline
from ecoscan.config import load_config
from ecoscan.image_processing.image_io import save_image
from ecoscan.segmentation.methods import apply_mask
from ecoscan.segmentation.morphology import OPERATIONS, apply_morphology
from ecoscan.services.visual_report import save_pipeline_artifacts, save_segmentation_comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, help="Optional authorized image; otherwise use a synthetic scene.")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "processing_lab")
    parser.add_argument("--kernel-size", type=int, choices=range(1, 16, 2), default=3)
    parser.add_argument("--kernel-shape", choices=["square", "cross", "disk"], default="square")
    parser.add_argument("--iterations", type=int, choices=range(1, 6), default=1)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = load_config()
    reference = None
    path = args.image
    if path is None:
        reference = np.zeros((96, 128), dtype=np.uint8)
        reference[20:76, 32:96] = 255
        noisy = reference.copy()
        noisy[46, 62] = 0
        noisy[10, 10] = 255
        image = np.full((96, 128, 3), 255, dtype=np.uint8)
        image[noisy > 0] = [35, 60, 90]
        path = save_image(image, output / "synthetic_input.png")
        save_image(reference, output / "reference_mask.png")
        config = replace(config, image_size=(128, 96))
    base = run_processing_pipeline(path, config, ProcessingPipelineOptions(
        filter_name="none", segmentation_name="otsu",
        segmentation_parameters={"invert": True if reference is not None else None}, morphology_name="none"))
    save_pipeline_artifacts(base, output / "control_pipeline")
    records, comparisons = [], []
    # All operations start from the SAME mask. They are not chained accidentally.
    for operation in OPERATIONS:
        result = apply_morphology(base.segmentation_result.mask, operation,
                                  kernel_size=args.kernel_size, kernel_shape=args.kernel_shape,
                                  iterations=args.iterations)
        segmented = replace(base.segmentation_result, name=operation, mask=result.mask,
                            image=apply_mask(base.filter_result.image, result.mask),
                            foreground_ratio=result.metadata["foreground_ratio_after"],
                            parameters=result.metadata, explanation=result.metadata["explanation"])
        comparisons.append(segmented)
        save_image(result.mask, output / f"{operation}_mask.png")
        save_image(result.gradient, output / f"{operation}_gradient.png")
        for i, (primitive, mask) in enumerate(result.stages, 1):
            save_image(mask, output / f"{operation}_{i:02d}_{primitive}.png")
        record = dict(result.metadata)
        if reference is not None:
            intersection = np.count_nonzero((reference > 0) & (result.mask > 0))
            union = np.count_nonzero((reference > 0) | (result.mask > 0))
            record["synthetic_iou"] = intersection / union if union else 1.0
        records.append(record)
    save_segmentation_comparison(comparisons, base.filter_result.image, output)
    from PIL import Image, ImageDraw, ImageFont
    canvas = Image.new("RGB", (1280, 650), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 17)
    except OSError:
        font = ImageFont.load_default()
    title = f"Mesma máscara | {args.kernel_shape} {args.kernel_size} x {args.kernel_size} | {args.iterations} iteração(ões)"
    draw.text((20, 18), title, fill="black", font=font)
    panels = [("Imagem preparada", base.filter_result.image),
              ("Referência sintética" if reference is not None else "Máscara de entrada",
               reference if reference is not None else base.segmentation_result.mask)]
    panels += [(OPERATIONS[row.name], row.mask) for row in comparisons]
    for index, (label, pixels) in enumerate(panels):
        x, y = (index % 4) * 320, 60 + (index // 4) * 295
        panel = Image.fromarray(pixels).convert("RGB")
        scale = min(280 / panel.width, 210 / panel.height)
        panel = panel.resize((round(panel.width * scale), round(panel.height * scale)),
                             Image.Resampling.NEAREST)
        canvas.paste(panel, (x + (320 - panel.width) // 2, y + (210 - panel.height) // 2))
        draw.text((x + 12, y + 228), label, fill="black", font=font)
    canvas.save(output / "morphology_overview.png")
    payload = {"synthetic": reference is not None, "recognition_evaluated": False,
               "same_source_mask": True, "operations": records}
    (output / "experiment.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Experimento de morfologia", "",
             "Todas as operações partem da mesma máscara Otsu, sem filtragem.",
             "IoU, quando presente, mede somente a máscara sintética, não o reconhecimento.", "",
             "| Operação | Pixels antes | Pixels depois | Alterados | IoU sintética |",
             "| --- | ---: | ---: | ---: | ---: |"]
    for record in records:
        iou = f"{record['synthetic_iou']:.6f}" if "synthetic_iou" in record else "não medida"
        lines.append(f"| {record['operation']} | {record['foreground_pixels_before']} | "
                     f"{record['foreground_pixels_after']} | {record['changed_pixels']} | {iou} |")
    (output / "experiment.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Experimento salvo em {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
