"""Integrity checks for private neural-head releases; no executable model payloads."""
import hashlib
import json
import re

from ecoscan.image_processing.contracts import processing_contract


def _verified_local(path, expected):
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return None
    return data if hashlib.sha256(data).hexdigest() == expected else None


def materialize(bucket, release, folder, config):
    identifier = release['id']
    if not re.fullmatch('[a-f0-9]{32}', identifier):
        raise ValueError('Invalid neural release ID')
    metadata_bytes = _verified_local(folder / 'semantic.json', release['metadata_sha256'])
    if metadata_bytes is None:
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
    # The caller revalidates consent before reaching this cache. Local files
    # remain untrusted until both hashes and the processing contract match.
    head = _verified_local(folder / 'head.npz', metadata['head_sha256'])
    if head is not None and _verified_local(folder / 'semantic.json', release['metadata_sha256']) is not None:
        return folder / 'semantic.json'
    if head is None:
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
