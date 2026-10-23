import hashlib
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ecoscan.services.semantic_release import materialize


@pytest.fixture
def release_data(tmp_path):
    original = tmp_path / 'semantic-v1'
    original.mkdir()
    head = b'checked-head'
    metadata = {'processing': {}, 'encoder_sha256': 'encoder', 'classes': ['metal', 'unknown'],
                'head_classes': ['metal'], 'head_sha256': hashlib.sha256(head).hexdigest()}
    data = json.dumps(metadata).encode()
    (original / 'semantic.json').write_bytes(data)
    config = SimpleNamespace(classes=['metal'], directories={'models': tmp_path})
    bucket = MagicMock()
    bucket.download.side_effect = lambda key: data if key.endswith('.json') else head
    release = {'id': 'a' * 32, 'metadata_sha256': hashlib.sha256(data).hexdigest()}
    with patch('ecoscan.services.semantic_release.processing_contract', return_value={}):
        yield bucket, release, tmp_path / 'remote', config


def test_unchanged_release_does_not_download_again(release_data):
    bucket, release, folder, config = release_data
    path = materialize(*release_data)
    assert bucket.download.call_count == 2
    bucket.download.reset_mock()
    assert materialize(*release_data) == path
    bucket.download.assert_not_called()


@pytest.mark.parametrize('filename', ['head.npz', 'semantic.json'])
def test_corrupt_cached_file_is_repaired(release_data, filename):
    bucket, release, folder, config = release_data
    materialize(*release_data)
    expected = (folder / filename).read_bytes()
    (folder / filename).write_bytes(b'corrupt')
    bucket.download.reset_mock()
    materialize(*release_data)
    assert (folder / filename).read_bytes() == expected
    assert bucket.download.call_count == 1


def test_cached_file_does_not_bypass_processing_contract(release_data):
    materialize(*release_data)
    with patch('ecoscan.services.semantic_release.processing_contract', return_value={'changed': True}):
        with pytest.raises(ValueError, match='Incompatible'):
            materialize(*release_data)
