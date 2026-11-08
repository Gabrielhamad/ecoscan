"""Synthetic fixtures validate export mechanics, never academic field results."""
import csv
from dataclasses import replace
import hashlib
import io
import json
import zipfile

import numpy as np
from PIL import Image
import pytest

from ecoscan.app.pipeline import run_processing_pipeline
from ecoscan.app.processing_options import ProcessingPipelineOptions
from ecoscan.config import load_config
from ecoscan.image_processing.preprocessing import to_grayscale
from ecoscan.services.processing_academic import load_reference_mask, segmentation_metrics
from ecoscan.services.processing_evidence import ProcessingEvidence, array_digest, processing_evidence_zip
from scripts.export_processing_evidence import main


@pytest.fixture
def photo(tmp_path):
    pixels = np.full((64, 80, 3), 245, dtype=np.uint8)
    pixels[12:50, 18:60] = (30, 90, 50)
    pixels[30, 30] = 255
    pixels[5, 5] = 0
    path = tmp_path / 'private-fixture.png'
    Image.fromarray(pixels).save(path)
    return path


@pytest.fixture
def pipeline(photo):
    return run_processing_pipeline(photo, load_config(), ProcessingPipelineOptions(
        filter_name='median', filter_parameters={'kernel_size': 3}, segmentation_name='otsu'))


def _decoded(archive, name):
    with Image.open(io.BytesIO(archive.read(name))) as image:
        return np.array(image)


def test_package_is_captured_execution_with_lossless_figures_and_hashes(pipeline):
    original = pipeline.loaded.array.copy()
    recognition = pipeline.recognition_image.copy()
    data = processing_evidence_zip(pipeline)
    # The same captured execution has identical ZIP bytes, including recorded timings.
    assert data == processing_evidence_zip(pipeline)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        assert manifest['schema_version'] == 3
        assert manifest['reference_quality'] is None
        assert manifest['input_file_sha256'] is None  # UI no longer has the encoded upload.
        assert manifest['source_kind'] == 'not_attested'
        assert not manifest['consent_recorded']
        assert manifest['classifier_input_sha256'] == array_digest(recognition)
        assert manifest['processing_contract'] == pipeline.metadata['recognition_preparation']['contract']
        assert manifest['timings_ms'] == pipeline.metadata['timings_ms']
        assert manifest['files_sha256'].keys() == set(archive.namelist()) - {'manifest.json'}
        for name, expected in manifest['files_sha256'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected
        for name, array in [('00_original_rgb.png', original),
                            ('intensity_before.png', to_grayscale(pipeline.preprocessing.resized)),
                            ('intensity_after.png', to_grayscale(pipeline.filter_result.image)),
                            ('components.png', pipeline.element_overlay),
                            ('contours.png', pipeline.morphology_result.gradient),
                            ('mask_raw.png', pipeline.raw_segmentation_result.mask),
                            ('mask_final.png', pipeline.segmentation_result.mask),
                            ('recognition_rgb.png', recognition),
                            ('06_classifier_input_after.png', recognition)]:
            np.testing.assert_array_equal(_decoded(archive, name), array)
        assert all(entry.date_time == (1980, 1, 1, 0, 0, 0) for entry in archive.infolist())
        report = archive.read('report.md').decode()
        assert 'IoU/Dice não medidos' in report
        assert 'private-fixture' not in report
        assert '| --- | --- | --- |\n|' in report  # Markdown table, no blank rows.
        assert 'components.png' in report and 'histogram_before.png' in report
        assert 'numpy' in manifest['runtime_versions']
        assert '4-neighbor' in manifest['implementations']['components']
        assert 'segmentation/morphology.py' in manifest['source_code_sha256']
    np.testing.assert_array_equal(pipeline.loaded.array, original)
    np.testing.assert_array_equal(pipeline.recognition_image, recognition)


def test_histogram_counts_and_parameter_matrix_come_from_actual_arrays(pipeline):
    with zipfile.ZipFile(io.BytesIO(processing_evidence_zip(pipeline))) as archive:
        rows = list(csv.DictReader(io.StringIO(archive.read('histogram.csv').decode())))
        assert len(rows) == 256
        for key, array in [('before_count', pipeline.preprocessing.resized),
                           ('after_count', pipeline.filter_result.image)]:
            expected = np.bincount(to_grayscale(array).ravel(), minlength=256)
            np.testing.assert_array_equal([int(row[key]) for row in rows], expected)
            assert sum(int(row[key]) for row in rows) == array.shape[0] * array.shape[1]
        parameters = list(csv.DictReader(io.StringIO(archive.read('parameters.csv').decode())))
        assert any(row == {'stage': '02_filter', 'parameter': 'kernel_size', 'value_json': '3'} for row in parameters)
        assert any(row['parameter'] == 'threshold' for row in parameters)


def test_differences_report_measured_mean_and_max_without_overflow():
    stage = ProcessingEvidence('id', 'difference', np.array([[[255, 0, 0], [10, 10, 10]]], np.uint8),
                               np.array([[[0, 0, 0], [10, 20, 10]]], np.uint8), {})
    manifest = stage.manifest()
    assert manifest['mean_absolute_difference'] == 132.5
    assert manifest['max_absolute_difference'] == 255
    assert manifest['changed_pixels'] == 2
    mismatch = replace(stage, after=np.zeros((2, 2), np.uint8)).manifest()
    assert mismatch['mean_absolute_difference'] is None
    assert mismatch['max_absolute_difference'] is None


def test_reference_reports_hand_computed_iou_dice_and_empty_convention(pipeline):
    predicted = np.array([[255, 255], [0, 0]], np.uint8)
    reference = np.array([[255, 0], [255, 0]], np.uint8)
    quality = segmentation_metrics(predicted, reference)
    assert quality['iou'] == pytest.approx(1 / 3)
    assert quality['dice'] == .5
    empty = np.zeros((2, 2), np.uint8)
    assert segmentation_metrics(empty, empty)['iou'] == 1
    assert segmentation_metrics(empty, reference)['dice'] == 0
    reference = pipeline.segmentation_result.mask.copy()
    with zipfile.ZipFile(io.BytesIO(processing_evidence_zip(pipeline, reference_mask=reference))) as archive:
        quality = json.loads(archive.read('manifest.json'))['reference_quality']
        assert quality['final']['iou'] == 1
        assert quality['final']['dice'] == 1
        assert quality['reference_sha256'] == array_digest(reference)
        np.testing.assert_array_equal(_decoded(archive, 'reference_mask.png'), reference)


@pytest.mark.parametrize('case', ['rgb', 'gray', 'size', 'orientation', 'format'])
def test_reference_rejects_silent_conversion_or_resizing(tmp_path, case):
    path = tmp_path / 'reference.png'
    image = Image.new('RGB' if case == 'rgb' else 'L', (3, 3) if case == 'size' else (4, 4),
                      color=128 if case == 'gray' else 0)
    exif = image.getexif()
    if case == 'orientation':
        exif[274] = 6
    image.save(path, format='JPEG' if case == 'format' else 'PNG', exif=exif)
    with pytest.raises(ValueError):
        load_reference_mask(path, (4, 4))


def test_binary_png_modes_preserve_annotation(tmp_path):
    path = tmp_path / 'reference.png'
    expected = np.array([[0, 255], [255, 0]], np.uint8)
    for mode in ('L', '1'):
        Image.fromarray(expected).convert(mode).save(path)
        np.testing.assert_array_equal(load_reference_mask(path, (2, 2)), expected)


def test_cli_comparison_preserves_exact_archive_bytes_and_records_provenance(photo, tmp_path, monkeypatch):
    import scripts.export_processing_evidence as exporter
    actual = exporter.run_processing_pipeline
    calls = []

    def record(path, config, options):
        calls.append(options.filter_name)
        return actual(path, config, options)

    monkeypatch.setattr(exporter, 'run_processing_pipeline', record)
    output = tmp_path / 'comparison'
    assert main(['--image', str(photo), '--output', str(output), '--source-kind', 'synthetic_fixture',
                 '--consent', '--compare-filters', '--segmentation', 'otsu']) == 0
    assert calls == ['none', 'gaussian', 'median', 'sobel']  # exactly once per variant
    with zipfile.ZipFile(output / 'evidence.zip') as archive:
        for name in archive.namelist():
            assert archive.read(name) == (output / name).read_bytes()
        masks = []
        for variant in calls:
            manifest = json.loads(archive.read(variant + '/manifest.json'))
            assert manifest['source_kind'] == 'synthetic_fixture'
            assert manifest['input_file_sha256'] == hashlib.sha256(photo.read_bytes()).hexdigest()
            assert manifest['consent_recorded']
            context = manifest['execution_context']
            assert context['options']['filter_name'] == variant
            assert not context['inference_executed']
            assert context['settings_file_sha256']
            assert manifest['reference_quality'] is None
            assert str(photo) not in json.dumps(manifest)
            masks.append(_decoded(archive, variant + '/02_filter_after.png'))
        assert not np.array_equal(masks[0], masks[2])
        assert 'none/report.md' in archive.read('report.md').decode()
        comparison = list(csv.DictReader(io.StringIO(archive.read('comparison.csv').decode())))
        assert len(comparison) == 4
        assert all(row['raw_iou'] == row['final_iou'] == row['final_dice'] == '' for row in comparison)


def test_cli_custom_options_and_human_reference(photo, tmp_path):
    reference = tmp_path / 'reference.png'
    # Arbitrary technical annotation, explicitly not field evidence.
    Image.new('L', (80, 64), 0).save(reference)
    options = tmp_path / 'options.json'
    options.write_text(json.dumps({'filter_parameters': {'kernel_size': 3},
                                   'segmentation_parameters': {'invert': True}}))
    output = tmp_path / 'reference-output'
    assert main(['--image', str(photo), '--output', str(output), '--source-kind', 'synthetic_fixture',
                 '--consent', '--filter', 'median', '--segmentation', 'otsu', '--options', str(options),
                 '--reference-mask', str(reference), '--reference-reviewed']) == 0
    manifest = json.loads((output / 'manifest.json').read_text())
    assert manifest['stages'][1]['parameters']['kernel_size'] == 3
    assert manifest['stages'][2]['parameters']['invert']
    assert manifest['reference_quality'] is not None
    assert manifest['execution_context']['reference_human_review_declared']


@pytest.mark.parametrize('case', ['no_consent', 'existing_output', 'reference_without_review',
                                 'review_without_reference', 'bad_reference', 'bad_options', 'corrupt_image'])
def test_cli_invalid_inputs_leave_no_partial_evidence(photo, tmp_path, case):
    output = tmp_path / 'invalid-output'
    args = ['--image', str(photo), '--output', str(output), '--source-kind', 'synthetic_fixture', '--consent']
    if case == 'no_consent':
        args.remove('--consent')
    elif case == 'existing_output':
        output.mkdir()
        (output / 'keep').write_text('existing data')
    elif case in {'reference_without_review', 'bad_reference'}:
        reference = tmp_path / 'invalid-reference.png'
        Image.new('L', (3, 3), 128).save(reference)
        args += ['--reference-mask', str(reference)]
        if case == 'bad_reference':
            args.append('--reference-reviewed')
    elif case == 'review_without_reference':
        args.append('--reference-reviewed')
    elif case == 'bad_options':
        options = tmp_path / 'invalid.json'
        options.write_text('{"unexpected": true}')
        args += ['--options', str(options)]
    elif case == 'corrupt_image':
        photo.write_bytes(b'not an image')
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    if case == 'existing_output':
        assert list(output.iterdir()) == [output / 'keep']
    else:
        assert not output.exists()


def test_export_does_not_change_classification_preparation(photo):
    config = load_config()
    options = ProcessingPipelineOptions(filter_name='none', segmentation_name='otsu')
    pipeline = run_processing_pipeline(photo, config, options)
    original = pipeline.recognition_image.copy()
    processing_evidence_zip(pipeline)
    np.testing.assert_array_equal(original, pipeline.recognition_image)
    without_morphology = run_processing_pipeline(photo, config, replace(options, morphology_name='none'))
    np.testing.assert_array_equal(original, without_morphology.recognition_image)


def test_cli_rejects_image_changed_during_processing(photo, tmp_path, monkeypatch):
    import scripts.export_processing_evidence as exporter
    actual = exporter.run_processing_pipeline

    def mutate(path, config, options):
        result = actual(path, config, options)
        Image.new('RGB', (80, 64), 'black').save(path)
        return result

    monkeypatch.setattr(exporter, 'run_processing_pipeline', mutate)
    output = tmp_path / 'changed-input'
    with pytest.raises(SystemExit) as error:
        main(['--image', str(photo), '--output', str(output), '--source-kind', 'synthetic_fixture', '--consent'])
    assert error.value.code == 2
    assert not output.exists()
