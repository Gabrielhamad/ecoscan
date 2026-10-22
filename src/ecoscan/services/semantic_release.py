"""Integrity checks for private neural-head releases; no executable model payloads."""
import hashlib
import json
import re

from ecoscan.image_processing.contracts import processing_contract


def materialize(bucket, release, folder, config):
    identifier = release['id']
    if not re.fullmatch('[a-f0-9]{32}', identifier):
        raise ValueError('Invalid neural release ID')
    metadata_bytes = bucket.download(f'runs/{identifier}/semantic.json')
    if hashlib.sha256(metadata_bytes).hexdigest() != release['metadata_sha256']:
        raise ValueError('Neural metadata checksum mismatch')
    metadata = json.loads(metadata_bytes)
    original = json.loads((config.directories['models'] / 'semantic-v1/semantic.json').read_text())
    if (metadata['processing'] != processing_contract(config)
            or metadata['encoder_sha256'] != original['encoder_sha256']
            or metadata['classes'] != original['classes']
            or set(metadata['head_classes']) != set(config.classes)):
        raise ValueError('Incompatible neural release')
    head = bucket.download(f'runs/{identifier}/head.npz')
    if hashlib.sha256(head).hexdigest() != metadata['head_sha256']:
        raise ValueError('Neural head checksum mismatch')
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / 'head.tmp'
    temporary.write_bytes(head)
    temporary.replace(folder / 'head.npz')
    temporary = folder / 'metadata.tmp'
    temporary.write_bytes(metadata_bytes)
    temporary.replace(folder / 'semantic.json')
    return folder / 'semantic.json'
