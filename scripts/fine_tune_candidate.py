"""Fine-tune MobileNetV2 on the exact EcoScan preparation and fixed reference split."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import cv2
import numpy as np
from sklearn.metrics import f1_score, log_loss

from ecoscan.app.pipeline import default_processing_options, run_processing_pipeline
from ecoscan.classification.deep_features import mobilenet_input
from ecoscan.config import load_config
from ecoscan.image_processing.contracts import processing_contract
from scripts.train_deep_candidate import _report
from ecoscan.training.review import fitting_split_mask


def main():
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset
    from torchvision.models import MobileNet_V2_Weights, mobilenet_v2

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--reference-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--epochs', type=int, default=8)
    parser.add_argument('--cases', type=Path)
    args = parser.parse_args()
    config = load_config()
    source, output = args.source.resolve(), args.output.resolve()
    if (not source.is_dir() or output.exists() or args.epochs < 2
            or output.is_relative_to(source) or source.is_relative_to(output)
            or output.is_relative_to(config.directories['models'])):
        raise ValueError('Use an existing source, at least two epochs and a new isolated output.')
    reference = json.loads((args.reference_run / 'training_summary.json').read_text(encoding='utf-8'))
    records = json.loads((args.reference_run / 'dataset_manifest.json').read_text(encoding='utf-8'))
    if reference['processing'] != processing_contract(config):
        raise ValueError('Reference preparation differs from current preparation.')
    if hashlib.sha256((args.reference_run / 'dataset_manifest.json').read_bytes()).hexdigest() != reference['manifest_sha256']:
        raise ValueError('Reference manifest integrity failed.')
    classes = sorted(config.classes)
    assigned = {}
    for row in records:
        path = (source / row['path']).resolve()
        if (not path.is_relative_to(source) or row['class_id'] not in classes
                or row['split'] not in {'train', 'validation', 'test'}
                or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']):
            raise ValueError('Reference data changed or contains invalid entries.')
        if row['group'] in assigned and assigned[row['group']] != row['split']:
            raise ValueError('Reference groups leak across splits.')
        assigned[row['group']] = row['split']
    output.mkdir(parents=True)
    torch.hub.set_dir(str(output / 'official_weights'))
    torch.set_num_threads(4)
    cv2.setNumThreads(2)
    random.seed(config.random_seed)
    np.random.seed(config.random_seed)
    torch.manual_seed(config.random_seed)
    torch.use_deterministic_algorithms(True)
    options = replace(default_processing_options(config), segmentation_name='none', morphology_name='none')

    def prepare(row):
        result = run_processing_pipeline(source / row['path'], config, options)
        return mobilenet_input(result.recognition_image)[0], {
            'path': row['path'], 'split': row['split'], 'group': row['group'],
            'sha256': row['sha256'], 'filter': result.metadata['filter']}

    arrays, evidence = [], []
    with ThreadPoolExecutor(max_workers=4) as executor:
        for index, (array, metadata) in enumerate(executor.map(prepare, records)):
            arrays.append(array)
            evidence.append(metadata)
            if (index + 1) % 100 == 0:
                print(f'Prepared {index + 1}/{len(records)}', flush=True)
    (output / 'preparation.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    images = torch.from_numpy(np.stack(arrays))
    del arrays
    labels = torch.tensor([classes.index(row['class_id']) for row in records])
    masks = {split: np.array(fitting_split_mask(records, split)) for split in ('train', 'validation', 'test')}
    loaders = {split: DataLoader(TensorDataset(images[mask], labels[mask]), batch_size=16,
                                shuffle=split == 'train', num_workers=0,
                                generator=torch.Generator().manual_seed(config.random_seed))
               for split, mask in masks.items()}
    model = mobilenet_v2(weights=MobileNet_V2_Weights.IMAGENET1K_V2)
    model.classifier[1] = nn.Linear(model.last_channel, len(classes))
    for parameter in model.features.parameters():
        parameter.requires_grad = False
    counts = torch.bincount(labels[masks['train']], minlength=len(classes)).float()
    if (counts == 0).any():
        raise ValueError('Training is missing a class.')
    loss_fn = nn.CrossEntropyLoss(weight=counts.sum() / (len(classes) * counts))
    optimizer = torch.optim.AdamW(model.classifier.parameters(), lr=1e-3, weight_decay=1e-4)

    def logits_for(loader):
        model.eval()
        logits, targets = [], []
        with torch.inference_mode():
            for batch, target in loader:
                logits.append(model(batch))
                targets.append(target)
        return torch.cat(logits), torch.cat(targets)

    best_score, best_state, stale, history = -1, None, 0, []
    for epoch in range(args.epochs):
        if epoch == 1:
            for block in model.features[14:]:
                for parameter in block.parameters():
                    parameter.requires_grad = True
            optimizer = torch.optim.AdamW([
                {'params': model.features[14:].parameters(), 'lr': 1e-5},
                {'params': model.classifier.parameters(), 'lr': 1e-4}], weight_decay=1e-4)
        model.train()
        # Keep pretrained batch-normalization statistics stable on a small dataset.
        for module in model.modules():
            if isinstance(module, nn.BatchNorm2d):
                module.eval()
        total_loss = 0
        for batch, target in loaders['train']:
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(batch), target)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5)
            optimizer.step()
            total_loss += float(loss.detach()) * len(batch)
        val_logits, val_labels = logits_for(loaders['validation'])
        score = float(f1_score(val_labels.numpy(), val_logits.argmax(1).numpy(), average='macro'))
        history.append({'epoch': epoch + 1, 'train_loss': total_loss / int(masks['train'].sum()),
                        'validation_macro_f1': score, 'fine_tuning': epoch >= 1})
        print(json.dumps(history[-1]), flush=True)
        if score > best_score:
            best_score, best_state, stale = score, copy.deepcopy(model.state_dict()), 0
        else:
            stale += 1
        if stale >= 3 and epoch >= 3:
            break
    model.load_state_dict(best_state)
    val_logits, val_labels = logits_for(loaders['validation'])
    temperature = min((.5, 1., 1.5, 2., 3.), key=lambda t: log_loss(
        val_labels.numpy(), torch.softmax(val_logits / t, dim=1).numpy(), labels=list(range(len(classes)))))
    val_probabilities = torch.softmax(val_logits / temperature, dim=1).numpy()
    val_targets = np.asarray(classes)[val_labels.numpy()]
    policies = [_report(val_targets, val_probabilities, classes, t) for t in (.5, .6, .7, .8, .9, .95)]
    eligible = [r for r in policies if r['accepted_count'] >= 20 and (r['accepted_accuracy'] or 0) >= .9]
    threshold = max(eligible, key=lambda r: r['coverage'])['threshold'] if eligible else .95
    test_logits, test_labels = logits_for(loaders['test'])
    test_probabilities = torch.softmax(test_logits / temperature, dim=1).numpy()
    test_targets = np.asarray(classes)[test_labels.numpy()]
    weights_path = output / 'fine_tuned.pth'
    torch.save(model.state_dict(), weights_path)
    metadata = {'architecture': 'torchvision_mobilenet_v2', 'classes': classes,
                'processing': processing_contract(config), 'threshold': threshold, 'temperature': temperature,
                'sha256': hashlib.sha256(weights_path.read_bytes()).hexdigest()}
    (output / 'fine_tuned.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    summary = {'history': history, 'validation_macro_f1': best_score,
               'validation': _report(val_targets, val_probabilities, classes, threshold),
               'test': _report(test_targets, test_probabilities, classes, threshold),
               'metadata': metadata, 'reference_manifest_sha256': reference['manifest_sha256'],
               'pretrained_weights': str(MobileNet_V2_Weights.IMAGENET1K_V2),
               'environment': {'torch': torch.__version__, 'device': 'cpu'},
               'active_model_changed': False,
               'limitations': ['Reference test reused: exploratory.',
                               'Temperature and threshold estimated on model-selection validation.',
                               'Material identity and unknown objects are not guaranteed.',
                               'No object boxes or live tracking.']}
    if args.cases:
        from ecoscan.classification.finetuned import FineTunedClassifier
        classifier = FineTunedClassifier.load(output, config)
        with args.cases.open(encoding='utf-8-sig', newline='') as file:
            cases = list(csv.DictReader(file))
        summary['regression_cases'] = []
        for row in cases:
            if row['expected_class'] not in classes:
                raise ValueError('Unknown expected class.')
            result = run_processing_pipeline((args.cases.parent / row['path']).resolve(), config)
            prediction = classifier.predict_image(result.recognition_image)
            summary['regression_cases'].append({'expected': row['expected_class'],
                'predicted': prediction.top_class_id, 'score': prediction.probability, 'accepted': prediction.accepted})
    (output / 'training_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(output), 'test': summary['test'], 'regression_cases': summary.get('regression_cases')}), flush=True)


if __name__ == '__main__':
    main()
