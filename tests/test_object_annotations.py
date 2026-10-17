import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image
import pytest

from ecoscan.training.object_annotations import coco_annotations, load_object_annotations, pixel_box


def fixture_manifest(tmp_path):
    image = tmp_path / 'photo.png'
    Image.new('RGB', (100, 80), 'green').save(image)
    entry = {'image_id': 'photo_1', 'file_name': 'photo.png',
             'sha256': hashlib.sha256(image.read_bytes()).hexdigest(), 'oriented_size': [100, 80],
             'group_id': 'object_1', 'split': 'regression', 'annotation_status': 'proposal',
             'objects': [{'object_id': 'box_1', 'object_type': 'bottle', 'material': 'glass',
                          'material_source': 'user_report', 'kind': 'single',
                          'box_xyxy_normalized': [.1, .2, .8, .9]}]}
    return {'schema_version': 1, 'images': [entry]}


def load(tmp_path, payload):
    manifest = tmp_path / 'annotations.json'
    manifest.write_text(json.dumps(payload), encoding='utf-8')
    return load_object_annotations(manifest, tmp_path, ['glass', 'metal'])


def test_material_is_independent_of_object_type_and_boxes_convert_correctly(tmp_path):
    payload = load(tmp_path, fixture_manifest(tmp_path))
    assert payload['images'][0]['objects'][0]['object_type'] == 'bottle'
    assert payload['images'][0]['objects'][0]['material'] == 'glass'
    assert pixel_box([.1, .2, .8, .9], 100, 80) == [10, 16, 80, 72]
    for box in ([0, 0, 2, 1], [0, .5, 1, .5], [0, 0, float('nan'), 1], [False, 0, 1, 1], None):
        with pytest.raises(ValueError):
            pixel_box(box, 100, 80)


def test_image_integrity_orientation_and_root_are_checked(tmp_path):
    original = fixture_manifest(tmp_path)
    for key, value in [('sha256', 'changed'), ('oriented_size', [80, 100]), ('file_name', '../outside.png')]:
        payload = copy.deepcopy(original)
        payload['images'][0][key] = value
        with pytest.raises(ValueError):
            load(tmp_path, payload)


def test_same_object_or_image_cannot_cross_splits(tmp_path):
    original = fixture_manifest(tmp_path)
    second_file = tmp_path / 'second.png'
    Image.new('RGB', (100, 80), 'red').save(second_file)
    second = copy.deepcopy(original['images'][0])
    second.update(image_id='photo_2', file_name='second.png', split='train',
                  sha256=hashlib.sha256(second_file.read_bytes()).hexdigest())
    original['images'].append(second)
    with pytest.raises(ValueError, match='crosses'):
        load(tmp_path, original)
    second.update(group_id='other_object', file_name='photo.png', sha256=original['images'][0]['sha256'])
    with pytest.raises(ValueError, match='crosses'):
        load(tmp_path, original)
    second['split'] = 'regression'
    with pytest.raises(ValueError, match='Duplicate image'):
        load(tmp_path, original)


def test_detector_export_requires_verified_individual_boxes_and_preserves_coco_dimensions(tmp_path):
    payload = fixture_manifest(tmp_path)
    with pytest.raises(ValueError, match='Regression'):
        coco_annotations(payload, 'regression', ['glass', 'metal'])
    image = payload['images'][0]
    image['split'] = 'train'
    with pytest.raises(ValueError, match='verified'):
        coco_annotations(payload, 'train', ['glass', 'metal'])
    image.update(annotation_status='verified', reviewed_by='test reviewer')
    validated = load(tmp_path, payload)
    exported = coco_annotations(validated, 'train', ['glass', 'metal'])
    assert exported['annotations'][0]['bbox'] == [10, 16, 70, 56]
    assert exported['annotations'][0]['area'] == 3920
    image['objects'][0]['kind'] = 'group'
    with pytest.raises(ValueError, match='individual'):
        coco_annotations(payload, 'train', ['glass', 'metal'])


def test_coco_export_writes_oriented_images_aligned_with_boxes(tmp_path):
    payload = fixture_manifest(tmp_path)
    original = tmp_path / 'oriented.jpg'
    exif = Image.Exif()
    exif[274] = 6
    Image.new('RGB', (100, 80), 'green').save(original, exif=exif)
    entry = payload['images'][0]
    entry.update(file_name='oriented.jpg', oriented_size=[80, 100], split='train',
                 sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                 annotation_status='verified', reviewed_by='test fixture')
    manifest = tmp_path / 'annotations.json'
    manifest.write_text(json.dumps(payload), encoding='utf-8')
    output = tmp_path / 'export'
    script = Path(__file__).resolve().parents[1] / 'scripts/evaluate_object_annotations.py'
    result = subprocess.run([sys.executable, str(script), '--annotations', str(manifest),
                             '--source-root', str(tmp_path), '--output', str(output), '--export-coco', 'train'],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    exported = json.loads((output / 'instances.json').read_text(encoding='utf-8'))
    assert exported['annotations'][0]['bbox'] == [8, 20, 56, 70]
    with Image.open(output / exported['images'][0]['file_name']) as image:
        assert image.size == (80, 100)
    with Image.open(original) as image:
        assert image.size == (100, 80)
