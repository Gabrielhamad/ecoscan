"""Synthetic local files only: provenance and leakage gates, never field accuracy."""
from copy import deepcopy
import csv
import json
import subprocess
import sys

import numpy as np
from PIL import Image
import pytest

from ecoscan.config import load_config
from ecoscan.services.evaluation_manifest import (
    CSV_FIELDS, audit_evaluation_manifest, build_local_manifest, verify_local_images,
)


@pytest.fixture
def collection(tmp_path):
    source = tmp_path / 'photos'
    source.mkdir()
    rows = []
    for index, (label, split) in enumerate([('plastic', 'train'), ('glass', 'validation'),
                                           ('metal', 'test'), ('unknown', 'test')]):
        name = f'fixture-{index}.png'
        pixels = np.random.default_rng(index).integers(0, 256, (64, 96, 3), dtype=np.uint8)
        Image.fromarray(pixels).save(source / name)
        rows.append(dict(zip(CSV_FIELDS, [name, label, split, f'object-{index}', f'session-{index}',
                                         'private-consent', 'true', 'synthetic_fixture',
                                         'out_of_scope' if label == 'unknown' else 'standard',
                                         'diffuse', 'plain', 'front'], strict=True)))
    return source, rows, tmp_path / 'collection.csv'


def write_collection(collection):
    source, rows, path = collection
    with path.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return source, path


def build(collection):
    source, path = write_collection(collection)
    return build_local_manifest(path, source, load_config())


def audit(rows):
    return audit_evaluation_manifest(rows, allowed_classes=(*load_config().classes, 'unknown'),
                                      require_provenance=True)


def test_builder_cli_freezes_hashes_without_copying_images(collection, tmp_path):
    source, csv_path = write_collection(collection)
    output = tmp_path / 'reports' / 'manifest.json'
    command = [sys.executable, 'scripts/build_field_manifest.py', '--csv', str(csv_path),
               '--source', str(source), '--output', str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    records = json.loads(output.read_text())
    assert len(records) == 4
    assert audit(records)['independent_test_confirmed'] is False
    assert records[-1]['class_id'] == 'unknown'
    assert records[0]['rgb_shape'] == [64, 96, 3]
    assert set(output.parent.iterdir()) == {output}
    assert subprocess.run(command, capture_output=True).returncode != 0
    verify_local_images(source, records, load_config())


@pytest.mark.parametrize(('key', 'value'), [('object_id', ''), ('session_id', ''), ('split', 'mixed'),
    ('class_id', 'invalid'), ('license', ''), ('consent', 'false'), ('consent', 'yes'),
    ('scenario', 'reflective_metal'), ('source_kind', 'guessed'), ('path', '../private.png'),
    ('path', '/absolute.png'), ('path', 'x/../fixture-0.png'), ('path', r'x\fixture-0.png')])
def test_builder_rejects_incomplete_or_unsafe_declarations(collection, key, value):
    collection[1][0][key] = value
    with pytest.raises((ValueError, OSError)):
        build(collection)


@pytest.mark.parametrize('field', ['object_id', 'session_id'])
def test_objects_and_sessions_cannot_cross_splits(collection, field):
    collection[1][2][field] = collection[1][0][field]
    with pytest.raises(ValueError, match=field):
        build(collection)


def test_repeated_angles_are_counted_but_never_split(collection):
    collection[1][3].update(object_id='object-2', session_id='session-2', class_id='metal', scenario='standard')
    assert audit(build(collection))['test_count'] == 2


def test_same_object_cannot_have_conflicting_labels(collection):
    collection[1][3].update(object_id='object-2')
    with pytest.raises(ValueError, match='Conflicting'):
        build(collection)


def test_exact_and_decoded_duplicates_are_rejected(collection):
    source, rows, _ = collection
    (source / rows[-1]['path']).write_bytes((source / rows[-2]['path']).read_bytes())
    with pytest.raises(ValueError, match='Repeated'):
        build(collection)
    with Image.open(source / rows[-2]['path']) as image:
        image.save(source / rows[-1]['path'], compress_level=0)
    with pytest.raises(ValueError, match='decoded RGB'):
        build(collection)


@pytest.mark.parametrize('kind', ['empty', 'corrupt', 'wrong-extension', 'symlink'])
def test_invalid_images_and_escaped_symlinks_are_rejected(collection, tmp_path, kind):
    source, rows, _ = collection
    path = source / rows[0]['path']
    if kind == 'empty':
        path.write_bytes(b'')
    elif kind == 'corrupt':
        path.write_bytes(b'not an image')
    elif kind == 'wrong-extension':
        Image.new('RGB', (64, 64)).save(path, format='BMP')
    else:
        outside = tmp_path / 'outside.png'
        path.rename(outside)
        path.symlink_to(outside)
    with pytest.raises(ValueError):
        build(collection)


def test_exif_and_transparency_use_existing_rgb_loader(collection):
    source, rows, _ = collection
    rows[0]['path'] = 'orientation.jpg'
    exif = Image.Exif()
    exif[274] = 6
    Image.fromarray(np.random.default_rng(9).integers(0, 256, (64, 96, 3), dtype=np.uint8)).save(source / rows[0]['path'], exif=exif)
    Image.new('RGBA', (64, 64), (100, 20, 10, 0)).save(source / rows[1]['path'])
    manifest = build(collection)
    assert manifest[0]['rgb_shape'] == [96, 64, 3]
    assert manifest[1]['original_mode'] == 'RGBA'
    verify_local_images(source, manifest, load_config())


def test_mutated_files_and_metadata_do_not_validate(collection):
    source, rows, _ = collection
    manifest = build(collection)
    for key in ('sha256', 'rgb_sha256', 'rgb_shape', 'format'):
        changed = deepcopy(manifest)
        changed[0][key] = 'changed'
        with pytest.raises(ValueError, match='changed'):
            verify_local_images(source, changed, load_config())
    (source / rows[0]['path']).write_bytes((source / rows[1]['path']).read_bytes())
    with pytest.raises(ValueError, match='changed'):
        verify_local_images(source, manifest, load_config())


def test_no_mixed_synthetic_field_or_claimed_independence(collection):
    manifest = build(collection)
    manifest[0]['source_kind'] = 'field_photo'
    with pytest.raises(ValueError, match='mix'):
        audit(manifest)
    manifest[0]['source_kind'] = 'synthetic_fixture'
    manifest[0]['independent_test'] = True
    with pytest.raises(ValueError, match='Independence'):
        audit(manifest)


def test_development_overlap_is_rejected(collection):
    manifest = build(collection)
    source, csv_path = write_collection(collection)
    with pytest.raises(ValueError, match='overlap'):
        build_local_manifest(csv_path, source, load_config(), [manifest[-1]['sha256']])


def test_empty_collection_yields_no_evidence(collection):
    collection[1].clear()
    with pytest.raises(ValueError, match='nonempty'):
        build(collection)
