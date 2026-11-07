"""Validation of image manifests before model evaluation.

This audits declared splits, file names, hashes, and optional object/session groups.
Passing does not independently establish provenance or real-world accuracy.
"""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Collection

from ecoscan.config import AppConfig
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.image_processing.validation import validate_image_file
from ecoscan.services.processing_evidence import array_digest


_SPLITS = frozenset({"train", "validation", "test"})
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_TOKEN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}\Z")
LICENSES = frozenset({'private-consent', 'CC0-1.0', 'CC-BY-4.0', 'CC-BY-SA-4.0'})
SCENARIOS = {'standard': None, 'transparent_plastic': 'plastic',
             'transparent_glass': 'glass', 'reflective_metal': 'metal', 'out_of_scope': 'unknown'}
CSV_FIELDS = ('path', 'class_id', 'split', 'object_id', 'session_id', 'license', 'consent',
              'source_kind', 'scenario', 'lighting', 'background', 'angle')


def validate_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or '\\' in value or '\x00' in value:
        raise ValueError('Invalid relative path')
    if PurePosixPath(value).is_absolute() or any(p in {'', '.', '..'} for p in value.split('/')) or ':' in value:
        raise ValueError('Unsafe image path')
    return value


def _provenance(record: dict[str, Any]) -> None:
    if not isinstance(record.get('license'), str) or record['license'] not in LICENSES or record.get('consent') is not True:
        raise ValueError('An allowed license and explicit consent=true are required')
    if not isinstance(record.get('source_kind'), str) or record['source_kind'] not in {'field_photo', 'synthetic_fixture'}:
        raise ValueError('Invalid source_kind')
    for name in ('object_id', 'session_id', 'lighting', 'background', 'angle'):
        value = record.get(name)
        if not isinstance(value, str) or not _TOKEN.fullmatch(value):
            raise ValueError(f'Invalid {name}: use an opaque token of up to 64 characters')
    scenario = record.get('scenario')
    if not isinstance(scenario, str) or scenario not in SCENARIOS:
        raise ValueError('Invalid scenario')
    if SCENARIOS[scenario] and SCENARIOS[scenario] != record['class_id']:
        raise ValueError('Scenario conflicts with class_id')
    if not isinstance(record.get('rgb_sha256'), str) or not _SHA256.fullmatch(record['rgb_sha256']):
        raise ValueError('Missing or invalid decoded RGB SHA-256')


def audit_evaluation_manifest(
    records: object,
    *,
    allowed_classes: Collection[str],
    require_groups: bool = False,
    development_hashes: Collection[str] = (),
    require_provenance: bool = False,
) -> dict:
    """Reject duplicate images, unsafe paths, and known split leakage.

    `require_groups` checks object/session separation *within the supplied
    manifest*. Historical training material not supplied here cannot be audited.
    """
    if not isinstance(records, list) or not records:
        raise ValueError("Manifest must contain a nonempty JSON list")

    allowed = set(allowed_classes)
    require_groups = require_groups or require_provenance
    seen_paths: set[str] = set()
    seen_hashes: set[str] = set()
    split_groups: dict[str, dict[str, set[str]]] = {
        name: {} for name in ("object_id", "session_id")
    }
    classes: Counter[str] = Counter()
    splits: Counter[str] = Counter()
    rgb_hashes: set[str] = set()
    object_labels: dict[str, str] = {}

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Invalid manifest entry {index}")
        split = record.get("split")
        class_id = record.get("class_id")
        path = record.get("path")
        digest = record.get("sha256")
        if not isinstance(split, str) or split not in _SPLITS:
            raise ValueError(f"Invalid split at entry {index}")
        if not isinstance(class_id, str) or class_id not in allowed:
            raise ValueError(f"Unsupported class at entry {index}")
        validate_relative_path(path)
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            raise ValueError(f"Invalid SHA-256 at entry {index}")
        if path in seen_paths or digest in seen_hashes:
            raise ValueError(f"Repeated file or image hash at entry {index}")
        seen_paths.add(path)
        seen_hashes.add(digest)
        splits[split] += 1
        if split == "test":
            classes[class_id] += 1
        if record.get('independent_test', False) is not False:
            raise ValueError('Independence cannot be asserted by manifest metadata')
        if require_provenance:
            _provenance(record)
            rgb_hash = record['rgb_sha256']
            if rgb_hash in rgb_hashes:
                raise ValueError('Repeated decoded RGB image')
            rgb_hashes.add(rgb_hash)

        if require_groups:
            for field, groups in split_groups.items():
                value = record.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"Missing {field} at entry {index}")
                groups.setdefault(value.strip(), set()).add(split)
            object_id = record['object_id'].strip()
            if object_id in object_labels and object_labels[object_id] != class_id:
                raise ValueError('Conflicting labels for object_id')
            object_labels[object_id] = class_id

    if not splits["test"]:
        raise ValueError("Manifest contains no test images")

    if require_groups:
        for field, groups in split_groups.items():
            if any(len(group_splits) > 1 for group_splits in groups.values()):
                raise ValueError(f"{field} crosses train/validation/test splits")
    if require_provenance and len({r['source_kind'] for r in records}) != 1:
        raise ValueError('Do not mix field photos and synthetic fixtures')

    if not all(isinstance(value, str) and _SHA256.fullmatch(value) for value in development_hashes):
        raise ValueError("Invalid development SHA-256")
    reference_hashes = set(development_hashes)
    test_hashes = {row["sha256"] for row in records if row["split"] == "test"}
    if test_hashes.intersection(reference_hashes):
        raise ValueError("Test images overlap the supplied development hashes")

    return {
        "records": len(records),
        "test_count": splits["test"],
        "test_support": dict(sorted(classes.items())),
        "split_counts": dict(sorted(splits.items())),
        "object_session_separation_checked": require_groups,
        "development_hashes_checked": len(reference_hashes),
        "independent_test_confirmed": False,
        "provenance_declarations_checked": require_provenance,
    }


def inspect_local_image(source: Path, record: dict[str, Any], config: AppConfig) -> dict[str, Any]:
    """Decode through the app's RGB/EXIF loader; never copy images or EXIF tags."""
    relative = validate_relative_path(record.get('path'))
    root = source.resolve(strict=True)
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Image resolves outside source root or is not a file')
    validate_image_file(path, allowed_extensions=config.allowed_extensions, min_size=config.min_image_size)
    with path.open('rb') as file:
        before = hashlib.file_digest(file, 'sha256').hexdigest()
    image = load_rgb_image(path, allowed_extensions=config.allowed_extensions, min_size=config.min_image_size)
    formats = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG'}
    if image.info.format != formats.get(Path(relative).suffix.lower()):
        raise ValueError('Encoded image format does not match extension')
    with path.open('rb') as file:
        if hashlib.file_digest(file, 'sha256').hexdigest() != before:
            raise ValueError('Image changed during inspection')
    return {'sha256': before, 'rgb_sha256': array_digest(image.array),
            'rgb_shape': list(image.array.shape), 'original_mode': image.info.mode,
            'format': image.info.format}


def verify_local_images(source: Path, records: list[dict[str, Any]], config: AppConfig) -> None:
    """Verify every supplied split before loading an encoder; no metadata-only bypass."""
    for index, record in enumerate(records):
        actual = inspect_local_image(source, record, config)
        for key in actual:
            if actual[key] != record.get(key):
                raise ValueError(f'Image metadata/hash changed at entry {index}: {key}')


def build_local_manifest(csv_path: Path, source: Path, config: AppConfig,
                         development_hashes: Collection[str] = ()) -> list[dict[str, Any]]:
    """Read explicit local labels/splits. Never infer object IDs, consent or splits."""
    with csv_path.open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None or set(reader.fieldnames) != set(CSV_FIELDS) or len(reader.fieldnames) != len(CSV_FIELDS):
            raise ValueError('CSV header must match the collection template')
        records = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError('Invalid CSV column count')
            if row['consent'] not in {'true', 'false'}:
                raise ValueError('consent must be true or false')
            record = {**row, 'consent': row['consent'] == 'true'}
            record.update(inspect_local_image(source, record, config))
            records.append(record)
    audit_evaluation_manifest(records, allowed_classes=(*config.classes, 'unknown'),
                              require_provenance=True, development_hashes=development_hashes)
    return records


def read_development_hashes(path: Path | None) -> list[str]:
    if path is None:
        return []
    hashes = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(hashes, list) or not all(isinstance(h, str) and _SHA256.fullmatch(h) for h in hashes):
        raise ValueError('Development hashes must be a JSON array of SHA-256 strings')
    return hashes
