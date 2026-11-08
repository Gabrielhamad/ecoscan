"""Mutation fixtures prove CI checks fail on relevant incompatible changes."""
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.check_architecture import check_architecture
from scripts.check_dependency_lock import check, locked_requirements
from scripts.check_model_integrity import check_metadata

ROOT = Path(__file__).resolve().parents[1]


def test_actual_architecture_and_dependency_declarations_pass():
    result = check_architecture(ROOT / 'src')
    assert result['modules'] > 100
    assert not result['violations'] and not result['eager_cycles']
    assert check(ROOT)['declarations_aligned']


def _module(source, name, content):
    path = source / 'ecoscan' / (name.replace('.', '/') + '.py')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.mark.parametrize('lazy', [False, True])
def test_domain_cannot_import_ui_even_inside_function(tmp_path, lazy):
    source = tmp_path / 'src'
    content = 'import ecoscan.ui.view\n'
    if lazy:
        content = 'def operation():\n    ' + content
    _module(source, 'image_processing.filters', content)
    assert check_architecture(source)['violations']


def test_relative_eager_cycle_fails_but_type_checking_is_excluded(tmp_path):
    source = tmp_path / 'src'
    _module(source, 'services.a', 'from . import b\n')
    _module(source, 'services.b', 'from . import a\n')
    assert check_architecture(source)['eager_cycles']
    _module(source, 'services.b', 'from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from . import a\n')
    assert not check_architecture(source)['eager_cycles']


@pytest.mark.parametrize('content', ['numpy>=1.26', 'numpy==2.5.4',
                                    'numpy==2.* --hash=sha256:' + 'a' * 64])
def test_unpinned_or_unhashed_lock_fails(tmp_path, content):
    path = tmp_path / 'requirements.lock'
    path.write_text(content)
    with pytest.raises(ValueError):
        locked_requirements(path)


@pytest.fixture
def model(tmp_path):
    folder = tmp_path / 'model'
    folder.mkdir()
    (folder / 'head.npz').write_bytes(b'technical head fixture')
    (folder / 'encoder_00.part').write_bytes(b'technical encoder fixture')
    def digest(name):
        return hashlib.sha256((folder / name).read_bytes()).hexdigest()
    contract = {'profile': {'version': 'technical-fixture'}, 'sha256': 'not-field-evidence'}
    metadata = {'processing': contract, 'classes': ['metal', 'unknown'], 'head_classes': ['metal'],
                'head_sha256': digest('head.npz'),
                'parts': [{'name': 'encoder_00.part', 'sha256': digest('encoder_00.part')}]}
    (folder / 'semantic.json').write_text(json.dumps(metadata))
    return folder, metadata, contract


def test_model_metadata_fixture_and_corruption_rejection(model):
    folder, metadata, contract = model
    assert check_metadata(folder, contract, ('metal',)) == metadata
    (folder / 'encoder_00.part').write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='checksum'):
        check_metadata(folder, contract, ('metal',))


@pytest.mark.parametrize('case', ['contract', 'head', 'scope', 'path'])
def test_model_gate_rejects_incompatible_artifact(model, case):
    folder, metadata, contract = model
    if case == 'contract':
        contract = {'different': True}
    elif case == 'head':
        (folder / 'head.npz').write_bytes(b'corrupt')
    elif case == 'scope':
        metadata['classes'].append('other')
    else:
        metadata['parts'][0]['name'] = '../encoder_00.part'
    (folder / 'semantic.json').write_text(json.dumps(metadata))
    with pytest.raises(ValueError):
        check_metadata(folder, contract, ('metal',))


def test_quality_workflow_has_read_only_token_pinned_actions_and_no_bypass():
    workflow = yaml.safe_load((ROOT / '.github/workflows/quality.yml').read_text())
    assert workflow['permissions'] == {'contents': 'read'}
    assert set(workflow['jobs']) == {'validation', 'security', 'community-database', 'container'}
    for job in workflow['jobs'].values():
        assert not job.get('continue-on-error')
        for step in job['steps']:
            assert not step.get('continue-on-error')
            if 'uses' in step:
                assert len(step['uses'].split('@')[1]) == 40
            if step.get('uses', '').startswith('actions/checkout@'):
                assert step['with']['persist-credentials'] is False
            if step.get('uses', '').startswith('actions/upload-artifact@'):
                paths = step['with']['path'].splitlines()
                assert paths and all('*' not in p for p in paths)
                assert all(Path(p).name in {'architecture.json', 'model-integrity.json', 'startup.json',
                                           'python.txt', 'dependencies.txt'} for p in paths)
    database = workflow['jobs']['community-database']
    assert database['services']['postgres']['image'] == 'postgres:16'
    assert any('for pass in 1 2' in step.get('run', '') for step in database['steps'])
