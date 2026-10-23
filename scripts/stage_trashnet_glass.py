"""Review glass from the verified official archive; no automatic label approval."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import random
import sys
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from import_trashnet import ARCHIVE_SHA256, signature, is_near_copy


def main():
    archive = ROOT / 'data/raw/trashnet_20261017/dataset-resized.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError('Official archive checksum mismatch')
    output = ROOT / 'reports/trashnet_glass_review_20261023'
    output.mkdir(exist_ok=False)
    reference = json.loads((ROOT / 'reports/recognition_experiment_20261022/dataset_manifest.json').read_text())
    known = []
    for row in reference:
        path = ROOT / 'reports/recognition_experiment_20261022_input/images' / row['path']
        with Image.open(path) as im:
            known.append(signature(np.asarray(ImageOps.exif_transpose(im).convert('RGB'))))
    rows = []
    with ZipFile(archive) as zip_file:
        names = sorted(n for n in zip_file.namelist() if n.startswith('dataset-resized/glass/') and n.endswith('.jpg'))
        random.Random(42).shuffle(names)
        for name in names:
            raw = zip_file.read(name)
            with Image.open(BytesIO(raw)) as im:
                image = ImageOps.exif_transpose(im).convert('RGB')
            identity = signature(np.asarray(image))
            if is_near_copy(identity, known):
                continue
            known.append(identity)
            filename = Path(name).name
            (output / filename).write_bytes(raw)
            rows.append({'path': filename, 'sha256': hashlib.sha256(raw).hexdigest(),
                         'group': 'trashnet_glass', 'class_id': 'glass',
                         'review_id': f'glass_{len(rows)+1:03d}',
                         'source_url': 'https://huggingface.co/datasets/garythung/trashnet',
                         'source_archive_sha256': ARCHIVE_SHA256, 'archive_entry': name,
                         'eligible_for_fit': False})
            if len(rows) == 48:
                break
    for offset in range(0, len(rows), 24):
        sheet = Image.new('RGB', (1200, 1440), 'white')
        draw = ImageDraw.Draw(sheet)
        for pos, row in enumerate(rows[offset:offset+24]):
            with Image.open(output / row['path']) as im:
                preview = ImageOps.contain(im.convert('RGB'), (290, 200))
            x, y = pos % 4 * 300, pos // 4 * 240
            sheet.paste(preview, (x, y))
            draw.text((x, y+202), row['review_id'] + ' ' + row['path'], fill='black')
        sheet.save(output / f'page_{offset//24+1}.jpg')
    (output / 'index.json').write_text(json.dumps(rows, indent=2))
    print(f'{len(rows)} new glass candidates; all pending visual review')


if __name__ == '__main__':
    main()
