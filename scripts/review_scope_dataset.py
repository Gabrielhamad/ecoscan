"""Stage TACO crops for visual review and export only explicit scope decisions."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from PIL import Image, ImageDraw, ImageOps
from ecoscan.services.recognition_scope import ITEMS, RECOGNITION_ITEMS


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--decisions', type=Path)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a new output directory.')
    capture = json.loads(args.capture.read_text(encoding='utf-8'))
    args.output.mkdir(parents=True)
    if args.decisions is None:
        rows = []
        for index, row in enumerate(capture):
            rows.append(dict(row, review_id=f'taco_{index + 1:03d}', action='pending'))
        for offset in range(0, len(rows), 24):
            page = rows[offset:offset + 24]
            sheet = Image.new('RGB', (1200, 240 * ((len(page) + 3) // 4)), 'white')
            draw = ImageDraw.Draw(sheet)
            for pos, row in enumerate(page):
                path = ROOT / row['local_path']
                if sha(path) != row['sha256']:
                    raise ValueError('Capture changed.')
                with Image.open(path) as im:
                    preview = ImageOps.contain(im.convert('RGB'), (290, 200))
                x, y = pos % 4 * 300, pos // 4 * 240
                sheet.paste(preview, (x, y))
                draw.text((x, y + 201), row['review_id'] + ' ' + row['taco_category'], fill='black')
            sheet.save(args.output / f'page_{offset // 24 + 1}.jpg')
        (args.output / 'index.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
        print(f'{len(rows)} proposals, none approved automatically.')
        return
    decisions = json.loads(args.decisions.read_text(encoding='utf-8'))
    if decisions['capture_sha256'] != sha(args.capture):
        raise ValueError('Review is not bound to this capture.')
    valid_ids = {f'taco_{i + 1:03d}' for i in range(len(capture))}
    if (not set(decisions['approved']).issubset(valid_ids)
            or not set(decisions.get('excluded', {})).issubset(valid_ids)
            or set(decisions['approved']) & set(decisions.get('excluded', {}))):
        raise ValueError('Unknown or conflicting review decisions.')
    # Compare decoded identities and perceptual hashes against every reference split.
    sys.path.insert(0, str(ROOT / 'scripts'))
    from import_trashnet import signature, is_near_copy
    import numpy as np
    known = []
    reference = json.loads(args.reference.read_text(encoding='utf-8'))
    reference_scenes = set()
    for row in reference:
        scene = re.search(r'_taco_(\d+)_\d+_', row['path'])
        if scene:
            reference_scenes.add(int(scene.group(1)))
        path = (args.source / row['path']).resolve()
        if not path.is_relative_to(args.source.resolve()) or sha(path) != row['sha256']:
            raise ValueError('Reference changed.')
        with Image.open(path) as im:
            known.append(signature(np.asarray(ImageOps.exif_transpose(im).convert('RGB'))))
    exported, rejected = [], []
    for index, row in enumerate(capture):
        key = f'taco_{index + 1:03d}'
        item = decisions['approved'].get(key)
        if item is None:
            rejected.append({'id': key, 'reason': decisions.get('excluded', {}).get(key, 'pending_review')})
            continue
        if row['taco_image_id'] in reference_scenes:
            rejected.append({'id': key, 'reason': 'same_source_scene_as_reference'})
            continue
        if item not in RECOGNITION_ITEMS or ITEMS[item][1] != row['class_id']:
            raise ValueError('Invalid object/material decision.')
        path = (ROOT / row['local_path']).resolve()
        if not path.is_relative_to(ROOT) or sha(path) != row['sha256']:
            raise ValueError('Capture changed.')
        with Image.open(path) as im:
            identity = signature(np.asarray(ImageOps.exif_transpose(im).convert('RGB')))
        if is_near_copy(identity, known):
            rejected.append({'id': key, 'reason': 'duplicate_or_near_duplicate_reference_or_batch'})
            continue
        target = args.output / row['class_id'] / path.name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(path, target)
        known.append(identity)
        exported.append(dict(row, path=target.relative_to(args.output).as_posix(),
                             item_id=item, split='train', group=f"taco_image_{row['taco_image_id']}",
                             review_id=key, review_method='assistant_visual_review',
                             eligible_for_fit=True))
    (args.output / 'manifest.json').write_text(json.dumps(exported, indent=2), encoding='utf-8')
    summary = {'approved_exported': len(exported), 'by_object': dict(Counter(r['item_id'] for r in exported)),
               'not_exported': rejected, 'reference_sha256': sha(args.reference),
               'decisions_sha256': sha(args.decisions), 'test_changed': False,
               'limitations': ['Crops, not full camera frames.', 'Scene groups do not establish physical-object identity.',
                              'Perceptual deduplication is heuristic; not a guarantee against leakage.',
                              'Assistant visual review, not expert material certification.']}
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    shutil.copy2(args.decisions, args.output / 'decisions.json')
    for name in ('source_config.json', 'source_annotations.json'):
        shutil.copy2(args.capture.parent / name, args.output / name)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
