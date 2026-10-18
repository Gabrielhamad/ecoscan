import cv2
import numpy as np
from ecoscan.image_processing.filters import apply_gaussian


def test_reported_kernel_reproduces_convolution_and_preserves_channels():
    image = np.random.default_rng(42).integers(0, 256, (80, 90, 3), dtype=np.uint8)
    result = apply_gaussian(image, kernel_size=3, sigma=.55)
    kernel = np.asarray(result.parameters['kernel_2d'])
    assert kernel.shape == (3, 3)
    assert abs(kernel.sum() - 1) < 1e-12
    reconstructed = cv2.filter2D(image, -1, kernel, borderType=cv2.BORDER_REFLECT_101)
    assert np.abs(reconstructed.astype(int) - result.image.astype(int)).max() <= 1
    assert result.image.shape == image.shape
