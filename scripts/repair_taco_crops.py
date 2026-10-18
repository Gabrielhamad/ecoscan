"""Rebuild a capture using EXIF orientation and preserve downloaded source bytes."""
import argparse
from io import BytesIO
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_taco_dataset import _sha256, _scaled_crop_box, USER_AGENT

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-cache', type=Path)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    records = json.loads(args.capture.read_text(encoding='utf-8'))
    annotations = json.loads((args.capture.parent / 'source_annotations.json').read_text(encoding='utf-8'))
    images = {r['id']: r for r in annotations['images']}
    repaired, rejected, cache = [], [], {}
    source_dir = args.output / 'source_images'
    source_dir.mkdir()
    for index, row in enumerate(records):
        scene = row['taco_image_id']
        try:
            if scene not in cache:
                cached = args.source_cache / f'{scene}.image' if args.source_cache else None
                if cached is not None and cached.is_file():
                    raw = cached.read_bytes()
                else:
                    request = Request(row['source_url'], headers={'User-Agent': USER_AGENT})
                    with urlopen(request, timeout=45) as response:
                        raw = response.read(30_000_001)
                if len(raw) > 30_000_000:
                    raise ValueError('Oversized source image.')
                path = source_dir / f'{scene}.image'
                path.write_bytes(raw)
                cache[scene] = path
            with Image.open(cache[scene]) as im:
                image = ImageOps.exif_transpose(im).convert('RGB')
            metadata = images[scene]
            ratio = metadata['width'] / metadata['height']
            if abs(image.width / image.height / ratio - 1) > .02:
                raise ValueError('Oriented image does not match annotation aspect ratio.')
            box = _scaled_crop_box(row['bbox_original'], source_width=metadata['width'],
                                  source_height=metadata['height'], actual_width=image.width,
                                  actual_height=image.height, margin_ratio=.12)
            if min(box[2] - box[0], box[3] - box[1]) < 48:
                raise ValueError('Crop too small after correct orientation.')
            crop = image.crop(box)
            buffer = BytesIO()
            crop.save(buffer, format='PNG')
            target = args.output / row['class_id'] / (Path(row['local_path']).stem + '.png')
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(buffer.getvalue())
            updated = dict(row, local_path=target.relative_to(ROOT).as_posix(), crop_box=list(box),
                           width=crop.width, height=crop.height, sha256=_sha256(buffer.getvalue()))
            repaired.append(updated)
            print(f'{index + 1}/{len(records)} rebuilt annotation {row["taco_annotation_id"]}', flush=True)
        except (OSError, ValueError) as exc:
            rejected.append({'annotation_id': row['taco_annotation_id'], 'reason': str(exc)})
            print(f'{index + 1}/{len(records)} rejected: {exc}', flush=True)
        (args.output / 'taco_capture_manifest.json').write_text(json.dumps(repaired, indent=2), encoding='utf-8')
    for name in ('source_config.json', 'source_annotations.json'):
        (args.output / name).write_bytes((args.capture.parent / name).read_bytes())
    (args.output / 'repair_summary.json').write_text(json.dumps({'repaired': len(repaired), 'rejected': rejected,
        'source_capture_sha256': _sha256(args.capture.read_bytes()),
        'source_hashes': {p.name: _sha256(p.read_bytes()) for p in source_dir.iterdir()}}, indent=2), encoding='utf-8')
    print(f'{len(repaired)} rebuilt, {len(rejected)} rejected.', flush=True)


if __name__ == '__main__':
    main()
