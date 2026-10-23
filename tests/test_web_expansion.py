import pytest

from scripts.train_web_expansion import batch_sources, scene_split, validate_batch_hashes


def test_scene_assignment_is_stable_and_does_not_depend_on_material():
    groups = [f'taco_image_{i}' for i in range(100)]
    assigned = {g: scene_split(g) for g in groups}
    assert set(assigned.values()) == {'train', 'test'}
    assert all(scene_split(g) == assigned[g] for g in reversed(groups))


def test_multiple_objects_from_same_scene_stay_together():
    rows = [{'group': 'taco_image_125', 'class_id': label}
            for label in ('metal', 'plastic', 'metal')]
    assert len({scene_split(row['group']) for row in rows}) == 1


@pytest.mark.parametrize('field', ['training_hashes', 'validation_hashes', 'held_out_hashes'])
def test_previous_training_and_evaluation_images_are_rejected(field):
    with pytest.raises(ValueError, match='already belongs'):
        validate_batch_hashes([{'sha256': 'existing'}], {field: ['existing']})


def test_duplicate_batch_images_are_rejected():
    with pytest.raises(ValueError, match='Duplicate'):
        validate_batch_hashes([{'sha256': 'same'}, {'sha256': 'same'}], {})


def test_new_images_are_allowed():
    validate_batch_hashes([{'sha256': 'new'}], {'training_hashes': ['old']})


def test_mixed_sources_are_not_misattributed_to_taco():
    assert batch_sources([
        {'taco_image_id': 1},
        {'source_archive_sha256': 'hash', 'archive_entry': 'glass/a.jpg',
         'source_url': 'https://huggingface.co/datasets/garythung/trashnet'},
    ]) == ['https://github.com/pedropro/TACO', 'https://huggingface.co/datasets/garythung/trashnet']


def test_unknown_source_is_rejected():
    with pytest.raises(ValueError, match='provenance'):
        batch_sources([{'source_url': 'https://example.org/photo.jpg'}])
