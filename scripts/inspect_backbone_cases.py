"""Inspect pretrained object hypotheses separately from waste-material labels."""
import argparse
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import cv2
import numpy as np
from torchvision.models import MobileNet_V2_Weights

from ecoscan.app.pipeline import default_processing_options, run_processing_pipeline
from ecoscan.classification.deep_features import MobileNetFeatures
from ecoscan.config import load_config
from dataclasses import replace
from ecoscan.image_processing.recognition_views import foreground_view


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backbone', type=Path, required=True)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--foreground', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a new output.')
    config = load_config()
    cv2.setNumThreads(2)
    backbone = MobileNetFeatures(args.backbone)
    names = MobileNet_V2_Weights.IMAGENET1K_V2.meta['categories']
    options = default_processing_options(config) if args.foreground else replace(default_processing_options(config), segmentation_name='none', morphology_name='none')
    with args.cases.open(encoding='utf-8-sig', newline='') as file:
        cases = list(csv.DictReader(file))
    results = []
    for row in cases:
        path = (args.cases.parent / row['path']).resolve()
        prepared = run_processing_pipeline(path, config, options)
        logits = backbone.extract(prepared.recognition_image)
        top = np.argsort(logits)[-5:][::-1]
        results.append({'case': path.name, 'expected_material': row['expected_class'],
                        'object_hypotheses': [{'name': names[int(i)], 'logit': float(logits[i])} for i in top]})
        if args.foreground:
            view, evidence = foreground_view(prepared.filter_result.image, prepared.segmentation_result.mask)
            logits = backbone.extract(view)
            top = np.argsort(logits)[-5:][::-1]
            results[-1]['foreground'] = evidence
            results[-1]['foreground_hypotheses'] = [{'name': names[int(i)], 'logit': float(logits[i])} for i in top]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {'label_space': 'ImageNet1K object categories; not waste material labels',
              'explicit_beverage_can_class': any(name in {'beer can', 'soda can', 'tin can'} for name in names),
              'cases': results}
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
