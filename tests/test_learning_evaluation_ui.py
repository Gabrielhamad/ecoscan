from unittest.mock import MagicMock

from ecoscan.ui.learning import render_evaluation


def test_no_completed_run_does_not_render_metrics():
    st = MagicMock()
    render_evaluation(st, [{'candidate_id': 'new', 'training_status': 'training',
                            'training_result': {'published': True}}])
    st.expander.assert_not_called()


def test_shared_batch_is_not_counted_twice_and_old_metrics_are_supported():
    st = MagicMock()
    st.selectbox.side_effect = lambda label, options, **kwargs: options[0]
    st.columns.return_value = [MagicMock(), MagicMock()]
    record = {'candidate_id': 'batch', 'training_status': 'validation_failed',
              'training_result': {'candidate_macro_f1': .6, 'reference_macro_f1': .7}}
    render_evaluation(st, [record, dict(record)])
    assert st.selectbox.call_args.args[1] == ['batch']
    st.caption.assert_called_with('Lote antigo: detalhamento por material não registrado.')


def test_completed_detailed_run_renders_per_class_metrics():
    st = MagicMock()
    st.selectbox.side_effect = lambda label, options, **kwargs: options[0]
    st.columns.return_value = [MagicMock(), MagicMock()]
    render_evaluation(st, [{'candidate_id': 'batch', 'training_status': 'validation_failed',
        'training_result': {'candidate_macro_f1': .6, 'reference_macro_f1': .7,
            'training_counts': {'metal': 12}, 'by_class': {'metal': {
                'support': 10, 'reference_recall': .8, 'candidate_recall': .7}},
            'gate_reasons': [{'code': 'recall_regression', 'class_id': 'metal'}]}}])
    assert st.dataframe.call_args.args[0][0]['Imagens de treino'] == 12
    st.write.assert_any_call('Queda de acerto no material: Metal')


def test_streamlit_can_render_completed_batch():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_string('''
import streamlit as st
from ecoscan.ui.learning import render_evaluation
render_evaluation(st, [{'candidate_id': 'batch', 'training_status': 'validation_failed',
    'training_result': {'candidate_macro_f1': .6, 'reference_macro_f1': .7,
        'training_counts': {'metal': 12}, 'by_class': {'metal': {
            'support': 10, 'reference_recall': .8, 'candidate_recall': .7}},
        'gate_reasons': [{'code': 'recall_regression', 'class_id': 'metal'}]}}])
''').run()
    assert not app.exception
    assert len(app.metric) == 2
    assert app.metric[1].value == '0.600'
    assert len(app.dataframe) == 1
