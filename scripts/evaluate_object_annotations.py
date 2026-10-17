"""Compare full-frame and manually annotated region classification, not detection."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import cv2
from PIL import Image, ImageDraw

from ecoscan.app.pipeline import run_processing_pipeline
from ecoscan.classification.deep_features import DeepFeatureClassifier
from ecoscan.config import load_config
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.training.object_annotations import coco_annotations, load_object_annotations, pixel_box


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotations', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--export-coco', choices=('train', 'validation', 'test'))
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a new output directory.')
    config = load_config()
    payload = load_object_annotations(args.annotations, args.source_root, config.classes)
    if args.export_coco:
        exported = coco_annotations(payload, args.export_coco, config.classes)
        args.output.mkdir(parents=True)
        (args.output / 'images').mkdir()
        selected = [image for image in payload['images'] if image['split'] == args.export_coco]
        for exported_image, original in zip(exported['images'], selected, strict=True):
            rgb = load_rgb_image(args.source_root / original['file_name'], allowed_extensions=config.allowed_extensions,
                                 min_size=config.min_image_size).array
            relative = f"images/{exported_image['id']:06d}.png"
            Image.fromarray(rgb).save(args.output / relative)
            exported_image['file_name'] = relative
            exported_image['source_sha256'] = original['sha256']
        (args.output / 'instances.json').write_text(json.dumps(exported, indent=2), encoding='utf-8')
        print('COCO bounding boxes exported with EXIF-oriented, RGB PNG images.')
        return
    if not args.candidate:
        parser.error('Provide --candidate for region evaluation.')
    if any(image['split'] == 'train' for image in payload['images']):
        raise ValueError('Region evaluation must not include training examples.')
    classifier = DeepFeatureClassifier.load(args.candidate, config)
    cv2.setNumThreads(2)
    args.output.mkdir(parents=True)
    predictions = []
    for image in payload['images']:
        source = args.source_root / image['file_name']
        full = run_processing_pipeline(source, config)
        full_prediction = classifier.predict_image(full.recognition_image)
        overlay = Image.fromarray(full.loaded.array.copy())
        draw = ImageDraw.Draw(overlay)
        width, height = overlay.size
        for obj in image['objects']:
            box = pixel_box(obj['box_xyxy_normalized'], width, height)
            # Lossless temporary crop, followed by the exact application preparation.
            with tempfile.TemporaryDirectory(prefix='ecoscan_region_') as temporary:
                path = Path(temporary) / 'region.png'
                Image.fromarray(full.loaded.array).crop(box).save(path)
                region = run_processing_pipeline(path, config)
                prediction = classifier.predict_image(region.recognition_image)
            expected = obj['material']
            predictions.append({'image_id': image['image_id'], 'object_id': obj['object_id'],
                'kind': obj['kind'], 'object_type': obj['object_type'], 'expected_material': expected,
                'annotation_status': image['annotation_status'], 'box_xyxy_pixels': box,
                'full_prediction': full_prediction.top_class_id, 'full_score': full_prediction.probability,
                'full_accepted': full_prediction.accepted,
                'region_prediction': prediction.top_class_id, 'region_score': prediction.probability,
                'region_accepted': prediction.accepted,
                'full_correct': full_prediction.top_class_id == expected if expected != 'unknown' else None,
                'region_correct': prediction.top_class_id == expected if expected != 'unknown' else None,
                'region_filter': region.metadata['filter'],
                'region_processing': region.metadata['recognition_preparation']})
            draw.rectangle(box, outline=(240, 180, 20), width=max(2, width // 250))
            draw.text((box[0] + 4, box[1] + 4), f"{obj['object_type']} / {expected}", fill=(200, 0, 0))
            Image.fromarray(region.recognition_image).save(args.output / f"region_{len(predictions):03d}.png")
        overlay.thumbnail((1200, 1200))
        overlay.save(args.output / f"annotation_{len(list(args.output.glob('annotation_*.jpg'))) + 1:03d}.jpg", quality=92)
    scored = [row for row in predictions if row['expected_material'] != 'unknown']
    report = {'scope': 'Known annotation diagnostic; manual boxes are not automatic detection or a blind test.',
              'annotation_sha256': hashlib.sha256(args.annotations.read_bytes()).hexdigest(),
              'model_sha256': hashlib.sha256((args.candidate / 'candidate.joblib').read_bytes()).hexdigest(),
              'images': len(payload['images']), 'regions': len(predictions),
              'annotation_status_counts': dict(Counter(image['annotation_status'] for image in payload['images'])),
              'scored_regions': len(scored), 'full_correct': sum(row['full_correct'] for row in scored),
              'region_correct': sum(row['region_correct'] for row in scored),
              'wrong_accepted_regions': sum(row['region_accepted'] and not row['region_correct'] for row in scored),
              'predictions': predictions, 'active_model_changed': False}
    (args.output / 'region_evaluation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('images', 'regions', 'full_correct', 'region_correct', 'wrong_accepted_regions')}))


if __name__ == '__main__':
    main()
