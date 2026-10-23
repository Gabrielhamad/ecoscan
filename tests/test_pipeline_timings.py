from PIL import Image
from ecoscan.app.pipeline import ProcessingPipelineOptions, run_processing_pipeline
from ecoscan.config import load_config


def test_pipeline_records_nonnegative_stage_timings_without_changing_input(tmp_path):
    image = tmp_path / 'sample.png'
    Image.new('RGB', (256, 256), (100, 120, 140)).save(image)
    result = run_processing_pipeline(image, load_config(), ProcessingPipelineOptions(
        filter_name='none', segmentation_name='none', morphology_name='none'))
    timings = result.metadata['timings_ms']
    assert set(timings) == {'decode', 'prepare', 'filter', 'segmentation', 'evidence_and_model_input', 'total'}
    assert all(value >= 0 for value in timings.values())
    assert abs(sum(value for key, value in timings.items() if key != 'total') - timings['total']) < 1
    assert result.recognition_image.shape == (224, 224, 3)
