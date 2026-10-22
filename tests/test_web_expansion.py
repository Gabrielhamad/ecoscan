from scripts.train_web_expansion import scene_split


def test_scene_assignment_is_stable_and_does_not_depend_on_material():
    groups = [f'taco_image_{i}' for i in range(100)]
    assigned = {g: scene_split(g) for g in groups}
    assert set(assigned.values()) == {'train', 'test'}
    assert all(scene_split(g) == assigned[g] for g in reversed(groups))


def test_multiple_objects_from_same_scene_stay_together():
    rows = [{'group': 'taco_image_125', 'class_id': label}
            for label in ('metal', 'plastic', 'metal')]
    assert len({scene_split(row['group']) for row in rows}) == 1
