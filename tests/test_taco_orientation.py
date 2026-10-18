from io import BytesIO
import json
import sys
import numpy as np
from PIL import Image
from scripts import capture_taco_dataset as capture


def test_download_applies_exif_before_annotation_coordinates(monkeypatch):
    pixels = np.zeros((80, 100, 3), dtype=np.uint8)
    pixels[:, :50] = (255, 0, 0)
    image = Image.fromarray(pixels)
    exif = Image.Exif()
    exif[274] = 6
    buffer = BytesIO()
    image.save(buffer, format='JPEG', exif=exif)
    raw = buffer.getvalue()
    monkeypatch.setattr(capture.urllib.request, 'urlopen', lambda *args, **kwargs: BytesIO(raw))
    result = capture._download_image('https://example.com/rotated.jpg')
    assert result.size == (80, 100)
    box = capture._scaled_crop_box([0, 0, 80, 50], source_width=80, source_height=100,
                                  actual_width=result.width, actual_height=result.height, margin_ratio=0)
    crop = np.asarray(result.crop(box))
    assert crop.shape == (50, 80, 3)
    assert crop[:, :, 0].mean() > 240
    assert crop[:, :, 1:].mean() < 10


def test_repair_accepts_relative_output_and_preserves_source(tmp_path, monkeypatch):
    from scripts import repair_taco_crops as repair
    source = tmp_path / 'capture'
    source.mkdir()
    image = Image.new('RGB', (100, 80), 'red')
    exif = Image.Exif()
    exif[274] = 6
    image.save(source / '1.image', format='JPEG', exif=exif)
    original = (source / '1.image').read_bytes()
    record = {'taco_image_id': 1, 'taco_annotation_id': 1, 'source_url': 'https://unused.test/photo',
              'class_id': 'plastic', 'local_path': 'old.png', 'bbox_original': [0, 0, 80, 100]}
    (source / 'capture.json').write_text(json.dumps([record]))
    (source / 'source_annotations.json').write_text(json.dumps({'images': [{'id': 1, 'width': 80, 'height': 100}]}))
    (source / 'source_config.json').write_text('{}')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(repair, 'ROOT', tmp_path)
    monkeypatch.setattr(sys, 'argv', ['repair', '--capture', 'capture/capture.json', '--output', 'rebuilt',
                                    '--source-cache', 'capture'])
    repair.main()
    result = json.loads((tmp_path / 'rebuilt/taco_capture_manifest.json').read_text())
    assert len(result) == 1
    assert (result[0]['width'], result[0]['height']) == (80, 100)
    assert (source / '1.image').read_bytes() == original
    assert (tmp_path / result[0]['local_path']).is_file()
