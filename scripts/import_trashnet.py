"""Download and import official TrashNet images, preserving the reference dataset."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
from urllib.request import urlopen
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import cv2
import numpy as np
from PIL import Image, ImageOps

from ecoscan.config import load_config
from ecoscan.image_processing.image_io import load_rgb_image

DATASET_URL = 'https://huggingface.co/datasets/garythung/trashnet/resolve/main/dataset-resized.zip'
LICENSE_URL = 'https://raw.githubusercontent.com/garythung/trashnet/master/LICENSE'
ARCHIVE_SHA256 = 'c060e8abfe5d6de0578ca15be1ed8ad0794a865d333c3473d53d1d9ad6e38b8c'
MAPPING = {'metal': 'metal', 'plastic': 'plastic', 'glass': 'glass',
           'paper': 'paper_cardboard', 'cardboard': 'paper_cardboard'}


def signature(rgb):
    gray = cv2.cvtColor(cv2.resize(rgb, (9, 8)), cv2.COLOR_RGB2GRAY)
    return (hashlib.sha256(str(rgb.shape).encode() + rgb.tobytes()).hexdigest(),
            int.from_bytes(np.packbits(gray[:, 1:] > gray[:, :-1]).tobytes(), 'big'))


def is_near_copy(candidate, known):
    digest, dhash = candidate
    return any(digest == other or (dhash ^ other_hash).bit_count() <= 4 for other, other_hash in known)


def download(url, path):
    if path.exists():
        return
    partial = path.with_suffix(path.suffix + '.partial')
    with urlopen(url, timeout=90) as response, partial.open('wb') as file:
        shutil.copyfileobj(response, file)
    partial.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--download-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = load_config()
    source, output = args.source.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('Use a new output isolated from the source.')
    reference = json.loads(args.reference.read_text(encoding='utf-8'))
    for row in reference:
        path = (source / row['path']).resolve()
        if not path.is_relative_to(source) or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Reference source changed or contains an invalid path.')
    args.download_dir.mkdir(parents=True, exist_ok=True)
    archive = args.download_dir / 'dataset-resized.zip'
    license_path = args.download_dir / 'LICENSE'
    download(DATASET_URL, archive)
    download(LICENSE_URL, license_path)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError('Dataset archive changed; review source before importing.')
    if 'MIT License' not in license_path.read_text(encoding='utf-8'):
        raise ValueError('Unexpected license file; review source before importing.')
    output.mkdir(parents=True)
    shutil.copy2(license_path, output / 'TRASHNET_LICENSE')
    known, imported, rejected = [], [], []
    for row in reference:
        path = source / row['path']
        rgb = load_rgb_image(path, allowed_extensions=config.allowed_extensions, min_size=config.min_image_size).array
        known.append(signature(rgb))
        destination = output / row['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    with ZipFile(archive) as zip_file:
        for entry in sorted(zip_file.infolist(), key=lambda item: item.filename):
            parts = PurePosixPath(entry.filename).parts
            if (entry.is_dir() or len(parts) != 3 or parts[0] != 'dataset-resized'
                    or parts[1] not in MAPPING or not parts[2].lower().endswith(('.jpg', '.jpeg', '.png'))):
                continue
            if entry.file_size > 20_000_000:
                raise ValueError('Unexpected oversized image in archive.')
            raw = zip_file.read(entry)
            try:
                with Image.open(BytesIO(raw)) as image:
                    rgb = np.asarray(ImageOps.exif_transpose(image).convert('RGB'), dtype=np.uint8)
                if min(rgb.shape[:2]) < 48:
                    raise ValueError('Image too small.')
            except (OSError, ValueError) as exc:
                rejected.append({'entry': entry.filename, 'reason': str(exc)})
                continue
            identity = signature(rgb)
            if is_near_copy(identity, known):
                rejected.append({'entry': entry.filename, 'reason': 'exact_or_dhash_near_copy'})
                continue
            label = MAPPING[parts[1]]
            destination = output / label / ('web_trashnet_' + parts[2])
            if destination.exists():
                raise ValueError('Dataset filename collision.')
            destination.parent.mkdir(exist_ok=True)
            destination.write_bytes(raw)
            known.append(identity)
            imported.append({'path': destination.relative_to(output).as_posix(), 'class_id': label,
                             'sha256': hashlib.sha256(raw).hexdigest(), 'decoded_sha256': identity[0],
                             'archive_entry': entry.filename, 'label_source': 'TrashNet publisher',
                             'individual_human_review': False, 'intended_split': 'train'})
    report = {'source': DATASET_URL, 'source_repository': 'https://github.com/garythung/trashnet',
              'authors': ['Gary Thung', 'Mindy Yang'], 'license': 'MIT', 'license_url': LICENSE_URL,
              'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
              'reference_sha256': hashlib.sha256(args.reference.read_bytes()).hexdigest(),
              'reference_count': len(reference), 'imported_counts': dict(Counter(row['class_id'] for row in imported)),
              'imported': imported, 'rejected': rejected, 'excluded_class': 'trash',
              'limitations': ['White-background capture domain.', 'dHash can reject distinct look-alike images.',
                              'Publisher labels imported; not an expert review of every image.',
                              'Does not add battery or electronic images.']}
    (output / 'web_provenance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'originals': len(reference), 'imported': len(imported),
                      'counts': report['imported_counts'], 'rejected': len(rejected)}), flush=True)


if __name__ == '__main__':
    main()
