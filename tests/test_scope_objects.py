from ecoscan.services.recognition_scope import ITEMS, RECOGNITION_ITEMS, REPORT_ITEMS


def test_initial_scope_is_closed_and_maps_to_existing_materials():
    assert len(RECOGNITION_ITEMS) == len(set(RECOGNITION_ITEMS)) == 12
    assert {ITEMS[item][1] for item in RECOGNITION_ITEMS} == {
        'metal', 'plastic', 'paper_cardboard', 'glass', 'battery', 'electronic'}
    assert ITEMS['household_cell'][1] == 'battery'


def test_old_broad_labels_remain_readable_but_are_not_new_report_choices():
    for item in ('battery', 'small_electronic'):
        assert item in ITEMS
        assert item not in REPORT_ITEMS
    assert 'unknown' in REPORT_ITEMS
    assert 'out_of_scope' in REPORT_ITEMS
