import hashlib
import io
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from ecoscan.training.semantic_learning import run, improvement
from ecoscan.app.pipeline import ProcessingPipelineOptions


def metrics(score=.7):
    return {'macro_f1': score, 'wrong_confident': 1,
            'by_class': {c: {'support': 20, 'recall': score} for c in ('metal', 'plastic')}}


def test_improvement_rejects_equal_and_regressing_classes():
    assert not improvement(metrics(), metrics(), ['metal', 'plastic'])
    assert improvement(metrics(.8), metrics(), ['metal', 'plastic'])
    bad = metrics(.8)
    bad['by_class']['metal']['recall'] = .5
    assert not improvement(bad, metrics(), ['metal', 'plastic'])


def test_idle_does_not_read_model_or_write_data():
    store = MagicMock()
    store.list.return_value = []
    assert run(SimpleNamespace(classes=['metal']), store) == 'idle'
    store.save.assert_not_called()


@pytest.mark.parametrize('passed', [True, False])
@pytest.mark.parametrize('previous_state', ['queued', 'validation_failed'])
def test_approved_report_trains_and_only_publishes_improvement(tmp_path, passed, previous_state):
    folder = tmp_path / 'semantic-v1'
    folder.mkdir()
    buffer = io.BytesIO()
    np.savez(buffer, train_x=np.ones((2, 2)), train_y=np.array(['metal', 'plastic']),
             validation_x=np.ones((2, 2)), validation_y=np.array(['metal', 'plastic']))
    data = buffer.getvalue()
    (folder / 'learning_seed.npz').write_bytes(data)
    (folder / 'learning_seed.json').write_text(json.dumps({
        'sha256': hashlib.sha256(data).hexdigest(), 'processing': {},
        'encoder_sha256': 'encoder', 'validation_hashes': []}))
    row = {'id': 'report', 'status': 'approved', 'consent': True, 'expected_class': 'metal',
           'revision': 1, 'training_status': previous_state, 'reviewed_at': 5}
    store = MagicMock()
    store.list.side_effect = lambda: [dict(row)]
    def save(record, **kwargs):
        row.update(record)
        return dict(row)
    store.save.side_effect = save
    store.image.return_value = b'private-photo'
    bucket = store.client.storage.from_.return_value
    bucket.list.return_value = []
    model = MagicMock()
    model.metadata = {'encoder_sha256': 'encoder'}
    model.image_features.return_value = np.ones(2)
    config = SimpleNamespace(classes=['metal', 'plastic'], directories={'models': tmp_path})
    with patch('ecoscan.training.semantic_learning.SemanticOnnxClassifier', return_value=model), \
         patch('ecoscan.training.semantic_learning.default_processing_options', return_value=ProcessingPipelineOptions()), \
         patch('ecoscan.training.semantic_learning.processing_contract', return_value={}), \
         patch('ecoscan.training.semantic_learning.run_processing_pipeline', return_value=SimpleNamespace(recognition_image=None)), \
         patch('ecoscan.training.semantic_learning.fit_head', return_value=({'coef': np.ones((2, 2))}, ['metal', 'plastic'])) as fit, \
         patch('ecoscan.training.semantic_learning.evaluate', side_effect=[metrics(.8 if passed else .6), metrics()]):
        assert run(config, store) == ('published' if passed else 'validation_failed')
    assert fit.call_args.args[1].shape == (3, 2)
    assert fit.call_args.args[2] == ['metal', 'plastic', 'metal']
    uploads = [call.args[0] for call in bucket.upload.call_args_list]
    assert ('semantic_active.json' in uploads) == passed
    assert not any('photo' in key for key in uploads)
    assert row['training_result']['seed_sha256'] == hashlib.sha256(data).hexdigest()


def test_unchanged_seed_does_not_retrain_a_completed_batch(tmp_path):
    folder = tmp_path / 'semantic-v1'
    folder.mkdir()
    (folder / 'learning_seed.json').write_text(json.dumps({'sha256': 'same-seed'}))
    store = MagicMock()
    store.list.return_value = [{'status': 'approved', 'consent': True, 'expected_class': 'metal',
        'training_status': 'validation_failed', 'training_result': {'seed_sha256': 'same-seed'}}]
    config = SimpleNamespace(classes=['metal'], directories={'models': tmp_path})
    assert run(config, store) == 'idle'
    store.save.assert_not_called()


def test_neural_release_verifies_hashes(tmp_path):
    from ecoscan.services.semantic_release import materialize
    folder = tmp_path / 'semantic-v1'
    folder.mkdir()
    head = b'non-executable-head'
    metadata = {'processing': {}, 'encoder_sha256': 'encoder', 'classes': ['metal', 'unknown'],
                'head_classes': ['metal'], 'head_sha256': hashlib.sha256(head).hexdigest()}
    (folder / 'semantic.json').write_text(json.dumps(metadata))
    data = json.dumps(metadata).encode()
    bucket = MagicMock()
    identifier = 'a' * 32
    bucket.download.side_effect = lambda key: data if key.endswith('.json') else head
    release = {'id': identifier, 'metadata_sha256': hashlib.sha256(data).hexdigest()}
    config = SimpleNamespace(classes=['metal'], directories={'models': tmp_path})
    with patch('ecoscan.services.semantic_release.processing_contract', return_value={}):
        path = materialize(bucket, release, tmp_path / 'remote', config)
        assert path.name == 'semantic.json'
        release['metadata_sha256'] = 'wrong'
        with pytest.raises(ValueError, match='checksum'):
            materialize(bucket, release, tmp_path / 'remote', config)
