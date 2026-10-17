"""Conservative foreground proposals; masks never replace the RGB pixels."""
from __future__ import annotations

import cv2
import numpy as np

from ecoscan.image_processing.preprocessing import letterbox_image


def foreground_view(rgb, mask, size=(224, 224)):
    if rgb.ndim != 3 or rgb.shape[2] != 3 or mask.shape != rgb.shape[:2]:
        raise ValueError('Foreground proposal needs aligned RGB and mask.')
    fallback, _ = letterbox_image(rgb, size)
    binary = (mask > 0).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if count <= 1:
        return fallback, {'applied': False, 'reason': 'no foreground'}
    chosen = 1 + int(stats[1:, cv2.CC_STAT_AREA].argmax())
    x, y, width, height, area = map(int, stats[chosen])
    frame_height, frame_width = rgb.shape[:2]
    foreground = int(binary.sum())
    ratio = area / (frame_height * frame_width)
    bbox_ratio = width * height / (frame_height * frame_width)
    dominant = area / foreground
    if not .05 <= ratio <= .85 or bbox_ratio > .9 or dominant < .6 or min(width, height) < 48:
        return fallback, {'applied': False, 'reason': 'ambiguous or insignificant proposal',
                          'component_ratio': ratio, 'dominant_fraction': dominant}
    padding = max(4, round(max(width, height) * .12))
    left, top = max(0, x - padding), max(0, y - padding)
    right, bottom = min(frame_width, x + width + padding), min(frame_height, y + height + padding)
    if (right - left) * (bottom - top) / (frame_width * frame_height) > .95:
        return fallback, {'applied': False, 'reason': 'proposal preserves essentially the whole frame'}
    crop = rgb[top:bottom, left:right]
    prepared, _ = letterbox_image(crop, size)
    return prepared, {'applied': True, 'box_xyxy': [left, top, right, bottom],
                      'component_ratio': ratio, 'dominant_fraction': dominant,
                      'scope': 'contrast-based region proposal; not a semantic object box'}
