"""Small, deterministic capture variations that preserve the whole object."""
from __future__ import annotations

import cv2
import numpy as np


AUGMENTATION_VERSION = "capture-v1"
VARIANT_NAMES = ("darker", "brighter", "tilted")


def capture_variants(rgb: np.ndarray):
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype != np.uint8:
        raise ValueError("Capture variations require RGB uint8 images.")
    # Simulate exposure without changing channel order or material hue.
    for name, gamma in (("darker", 1.25), ("brighter", 0.8)):
        table = np.rint(255 * (np.arange(256) / 255.0) ** gamma).astype(np.uint8)
        yield name, cv2.LUT(rgb, table)
    height, width = rgb.shape[:2]
    transform = cv2.getRotationMatrix2D((width / 2, height / 2), 7, 1)
    cosine, sine = abs(transform[0, 0]), abs(transform[0, 1])
    expanded = (int(np.ceil(width * cosine + height * sine)),
                int(np.ceil(height * cosine + width * sine)))
    transform[:, 2] += [(expanded[0] - width) / 2, (expanded[1] - height) / 2]
    yield "tilted", cv2.warpAffine(rgb, transform, expanded,
                                  flags=cv2.INTER_LINEAR, borderValue=(127, 127, 127))


def training_indices(splits):
    """Fail closed on unexpected splits before generating any synthetic image."""
    if not splits or any(split not in {"train", "validation", "test"} for split in splits):
        raise ValueError("Invalid dataset split.")
    return [index for index, split in enumerate(splits) if split == "train"]
