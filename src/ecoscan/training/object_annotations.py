"""Object/material annotations with immutable image identity and split checks."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageOps


def pixel_box(box, width, height):
    if (not isinstance(box, (list, tuple)) or len(box) != 4 or any(isinstance(v, bool) or not isinstance(v, (float, int))
                             or not math.isfinite(v) for v in box)):
        raise ValueError('Bounding box must contain four finite normalized coordinates.')
    left, top, right, bottom = box
    if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
        raise ValueError('Bounding box is outside the image or empty.')
    return [math.floor(left * width), math.floor(top * height),
            math.ceil(right * width), math.ceil(bottom * height)]


def load_object_annotations(manifest_path: Path, source_root: Path, classes):
    payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    if payload.get('schema_version') != 1 or not payload.get('images'):
        raise ValueError('Unsupported or empty object annotation manifest.')
    root = source_root.resolve()
    ids, groups, hashes = set(), {}, {}
    for image in payload['images']:
        split = image['split']
        if (not image['image_id'] or image['image_id'] in ids or not image['group_id']
                or split not in {'train', 'validation', 'test', 'regression'}
                or image['annotation_status'] not in {'proposal', 'verified'}):
            raise ValueError('Invalid image identity, annotation status or split.')
        ids.add(image['image_id'])
        path = (root / image['file_name']).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError('Annotation image must be inside the source root.')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != image['sha256']:
            raise ValueError('Annotated image changed.')
        if digest in hashes and hashes[digest] == split:
            raise ValueError('Duplicate image identity within the annotation set.')
        for registry, key in ((groups, image['group_id']), (hashes, digest)):
            if key in registry and registry[key] != split:
                raise ValueError('Object group or exact image crosses dataset splits.')
            registry[key] = split
        with Image.open(path) as original:
            width, height = ImageOps.exif_transpose(original).size
        if [width, height] != image['oriented_size']:
            raise ValueError('Annotation dimensions do not match EXIF-oriented image.')
        object_ids = set()
        for obj in image['objects']:
            if (not obj['object_id'] or obj['object_id'] in object_ids
                    or not obj['object_type'].strip() or obj['material'] not in {*classes, 'unknown'}
                    or obj['kind'] not in {'single', 'group'}
                    or obj['material_source'] not in {'user_report', 'dataset_publisher', 'analyst_verified', 'unknown'}):
                raise ValueError('Invalid object or material annotation.')
            object_ids.add(obj['object_id'])
            pixel_box(obj['box_xyxy_normalized'], width, height)
        if image['annotation_status'] == 'verified' and not image.get('reviewed_by', '').strip():
            raise ValueError('Verified annotations require a named reviewer.')
    return payload


def coco_annotations(payload, split, classes):
    if split not in {'train', 'validation', 'test'}:
        raise ValueError('Regression images cannot be exported as detector training data.')
    category_ids = {label: i + 1 for i, label in enumerate(sorted(classes))}
    result = {'images': [], 'annotations': [],
              'categories': [{'id': value, 'name': key} for key, value in category_ids.items()]}
    for image in payload['images']:
        if image['split'] != split:
            continue
        if image['annotation_status'] != 'verified':
            raise ValueError('Detector export requires verified annotations.')
        width, height = image['oriented_size']
        image_id = len(result['images']) + 1
        result['images'].append({'id': image_id, 'file_name': image['file_name'], 'width': width, 'height': height})
        for obj in image['objects']:
            if obj['kind'] != 'single' or obj['material'] == 'unknown':
                raise ValueError('Detector export requires individual boxes with known material.')
            left, top, right, bottom = pixel_box(obj['box_xyxy_normalized'], width, height)
            result['annotations'].append({'id': len(result['annotations']) + 1, 'image_id': image_id,
                'category_id': category_ids[obj['material']], 'bbox': [left, top, right - left, bottom - top],
                'area': (right - left) * (bottom - top), 'iscrowd': 0,
                'object_type': obj['object_type'], 'box_only': True})
    if not result['images']:
        raise ValueError('No verified images available for this split.')
    return result
