from unittest.mock import MagicMock, patch

from PIL import Image
import pytest

from ecoscan.image_processing.validation import ImageValidationError, validate_image_file


def test_byte_limit_rejects_before_open(tmp_path):
    path = tmp_path / 'image.jpg'
    path.write_bytes(b'0123456789')
    with patch('ecoscan.image_processing.validation.Image.open') as opened:
        with pytest.raises(ImageValidationError, match='Arquivo muito grande'):
            validate_image_file(path, allowed_extensions={'.jpg'}, min_size=(1, 1), max_file_bytes=5)
        opened.assert_not_called()


def test_pixel_limit_rejects_before_verify_or_decode(tmp_path):
    path = tmp_path / 'image.jpg'
    path.write_bytes(b'header')
    header = MagicMock(width=10000, height=10000)
    with patch('ecoscan.image_processing.validation.Image.open') as opened:
        opened.return_value.__enter__.return_value = header
        with pytest.raises(ImageValidationError, match='Resolucao'):
            validate_image_file(path, allowed_extensions={'.jpg'}, min_size=(1, 1))
        header.verify.assert_not_called()
        header.load.assert_not_called()


def test_pillow_decompression_error_is_user_validation_error(tmp_path):
    path = tmp_path / 'image.jpg'
    path.write_bytes(b'header')
    with patch('ecoscan.image_processing.validation.Image.open', side_effect=Image.DecompressionBombError):
        with pytest.raises(ImageValidationError, match='Resolucao'):
            validate_image_file(path, allowed_extensions={'.jpg'}, min_size=(1, 1))


def test_valid_image_at_configured_pixel_limit(tmp_path):
    path = tmp_path / 'image.png'
    Image.new('RGB', (20, 20)).save(path)
    result = validate_image_file(path, allowed_extensions={'.png'}, min_size=(1, 1), max_pixels=400)
    assert (result.width, result.height) == (20, 20)
