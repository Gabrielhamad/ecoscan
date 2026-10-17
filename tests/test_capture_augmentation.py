import numpy as np
import pytest

from ecoscan.training.augmentation import capture_variants, training_indices


def test_capture_variants_preserve_color_geometry_and_are_reproducible():
    image = np.full((80, 120, 3), [60, 120, 180], dtype=np.uint8)
    variants = dict(capture_variants(image))
    assert variants.keys() == {'darker', 'brighter', 'tilted'}
    assert variants['darker'].mean() < image.mean() < variants['brighter'].mean()
    assert variants['tilted'].shape[0] > 80 and variants['tilted'].shape[1] > 120
    for name, variant in capture_variants(image):
        assert variant.dtype == np.uint8
        np.testing.assert_array_equal(variant, variants[name])
        center = variant[variant.shape[0] // 2, variant.shape[1] // 2]
        assert center[0] < center[1] < center[2]
    np.testing.assert_array_equal(image[0, 0], [60, 120, 180])


def test_variations_never_select_validation_or_test_parents():
    assert training_indices(['test', 'train', 'validation', 'train']) == [1, 3]
    with pytest.raises(ValueError):
        training_indices(['train', 'unknown'])
    with pytest.raises(ValueError):
        list(capture_variants(np.zeros((10, 10), dtype=np.uint8)))
