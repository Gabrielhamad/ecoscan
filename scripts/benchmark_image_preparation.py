"""Paired synthetic-degradation benchmark on real photos; not recognition accuracy."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from skimage.metrics import structural_similarity

from ecoscan.config import load_config
from ecoscan.image_processing.adaptive_filters import apply_adaptive_filter_pipeline, _preservation
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.image_processing.preprocessing import prepare_working_image


def degrade(image, kind, rng):
    if kind == 'unchanged':
        return image.copy()
    if kind == 'gaussian_noise':
        return np.clip(image.astype(float) + rng.normal(0, 12, image.shape), 0, 255).astype(np.uint8)
    if kind == 'impulse_noise':
        result = image.copy()
        mask = rng.random(image.shape[:2])
        result[mask < .005] = 0
        result[mask > .995] = 255
        return result
    if kind == 'low_contrast':
        return np.clip((image.astype(float) - 127) * .35 + 127, 0, 255).astype(np.uint8)
    raise ValueError('Unknown controlled degradation.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--min-noise-sigma', type=float)
    args = parser.parse_args()
    source = args.source.resolve()
    if args.output.exists():
        raise ValueError('Use a new output directory.')
    config = load_config()
    records = json.loads(args.manifest.read_text(encoding='utf-8'))
    args.output.mkdir(parents=True)
    rows = []
    cv2.setNumThreads(2)
    for index, row in enumerate(records):
        path = (source / row['path']).resolve()
        if not path.is_relative_to(source) or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Source changed.')
        clean = prepare_working_image(load_rgb_image(path, allowed_extensions=config.allowed_extensions,
                    min_size=config.min_image_size).array, 640).resized
        seed = int(row['sha256'][:8], 16)
        for kind in ('unchanged', 'gaussian_noise', 'impulse_noise', 'low_contrast'):
            degraded = degrade(clean, kind, np.random.default_rng(seed))
            overrides = {'min_noise_sigma': args.min_noise_sigma} if args.min_noise_sigma is not None else None
            result = apply_adaptive_filter_pipeline(degraded, config.filters, overrides=overrides)
            restored = result.filter_result.image
            def similarity(image):
                return float(structural_similarity(clean, image, channel_axis=-1, data_range=255))
            before, after = similarity(degraded), similarity(restored)
            rows.append({'path': row['path'], 'sha256': row['sha256'], 'condition': kind,
                         'selected': result.decision['selected'], 'reference_ssim_before': before,
                         'reference_ssim_after': after, 'delta_ssim': after - before,
                         'preservation': _preservation(degraded, restored), 'decision': result.decision})
            if index < 3:
                sheet = Image.new('RGB', (960, 285), 'white')
                draw = ImageDraw.Draw(sheet)
                for column, (title, pixels) in enumerate((('Reference photo', clean), ('Controlled input', degraded),
                                                        ('Prepared: ' + result.decision['selected'], restored))):
                    preview = ImageOps.contain(Image.fromarray(pixels), (310, 250))
                    sheet.paste(preview, (column * 320, 25))
                    draw.text((column * 320 + 4, 5), title, fill='black')
                sheet.save(args.output / f'{index + 1:02d}_{kind}.jpg')
        print(f'Benchmarked {index + 1}/{len(records)}', flush=True)
    summary = {}
    for kind in ('unchanged', 'gaussian_noise', 'impulse_noise', 'low_contrast'):
        selected = [r for r in rows if r['condition'] == kind]
        summary[kind] = {'count': len(selected), 'filters': dict(Counter(r['selected'] for r in selected)),
                         'mean_delta_ssim': float(np.mean([r['delta_ssim'] for r in selected])),
                         'improved': sum(r['delta_ssim'] > 1e-6 for r in selected),
                         'worsened': sum(r['delta_ssim'] < -1e-6 for r in selected)}
    payload = {'summary': summary, 'min_noise_sigma_override': args.min_noise_sigma,
               'manifest_sha256': hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
               'rows': rows, 'limitations': ['Synthetic corruptions, not camera performance.',
                    'Reference photos may already contain noise or blur.',
                    'SSIM improvement does not establish recognition improvement.']}
    (args.output / 'benchmark.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
