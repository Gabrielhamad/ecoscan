"""Create numbered training-only contact sheets for a visual label review."""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a new review directory.')
    source = args.source.resolve()
    records = json.loads(args.manifest.read_text(encoding='utf-8'))
    grouped = defaultdict(list)
    for row in records:
        if row['split'] != 'train':
            continue
        path = (source / row['path']).resolve()
        if not path.is_relative_to(source) or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Training source changed or has an invalid path.')
        grouped[row['class_id']].append(row)
    args.output.mkdir(parents=True)
    index = []
    for label, rows in grouped.items():
        for offset in range(0, len(rows), 48):
            page = rows[offset:offset + 48]
            sheet = Image.new('RGB', (1200, 40 + ((len(page) + 5) // 6) * 180), 'white')
            draw = ImageDraw.Draw(sheet)
            draw.text((10, 10), f'{label} - training only - page {offset // 48 + 1}', fill='black')
            for position, row in enumerate(page):
                with Image.open(source / row['path']) as photo:
                    preview = ImageOps.contain(ImageOps.exif_transpose(photo).convert('RGB'), (190, 150))
                x, y = (position % 6) * 200, 40 + (position // 6) * 180
                sheet.paste(preview, (x + (200 - preview.width) // 2, y))
                review_id = f'{label}_{offset + position + 1:03d}'
                draw.text((x + 5, y + 151), review_id, fill='black')
                index.append({'review_id': review_id, 'path': row['path'], 'class_id': label,
                              'sha256': row['sha256'], 'action': 'pending', 'reason': ''})
            sheet.save(args.output / f'{label}_{offset // 48 + 1:02d}.jpg', quality=92)
    with (args.output / 'review_index.csv').open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['review_id', 'path', 'class_id', 'sha256', 'action', 'reason'])
        writer.writeheader()
        writer.writerows(index)
    print(f'{len(index)} training images indexed; validation and test not exported.')


if __name__ == '__main__':
    main()
