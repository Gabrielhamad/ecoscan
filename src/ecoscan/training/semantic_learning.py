"""Private reviewed learning for the deployed frozen neural encoder."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from ecoscan.app.pipeline import default_processing_options, run_processing_pipeline
from ecoscan.classification.semantic_onnx import SemanticOnnxClassifier
from ecoscan.image_processing.contracts import processing_contract
from ecoscan.metrics.classification_metrics import classification_report
from ecoscan.training.automatic import BUCKET, eligible, update_rows
from ecoscan.training.diagnostics import evaluation_details


def improvement(candidate, reference, classes):
    """Assisted hypotheses only: improve macro F1 without per-class recall loss."""
    return (candidate['macro_f1'] > reference['macro_f1'] + .005
            and all(candidate['by_class'][c]['support'] >= 10
                    and candidate['by_class'][c]['recall'] >= reference['by_class'][c]['recall']
                    for c in classes))


def fit_head(base, features, labels):
    if set(labels) != set(base.metadata['head_classes']):
        raise ValueError('Training classes do not match the neural model')
    scaler = StandardScaler().fit(features)
    head = LogisticRegression(C=.1, class_weight='balanced', max_iter=2500, random_state=42)
    head.fit(scaler.transform(features), labels)
    candidate = deepcopy(base.arrays)
    candidate.update(mean=scaler.mean_, scale=scaler.scale_, coef=head.coef_, intercept=head.intercept_)
    return candidate, list(head.classes_)


def evaluate(model, features, labels, classes):
    predictions = [model.predict_features(x) for x in features]
    report = classification_report(labels, [p.top_class_id for p in predictions], list(classes))
    report['wrong_confident'] = sum(p.accepted and p.top_class_id != y for p, y in zip(predictions, labels))
    return report


def run(config, store):
    rows = eligible(store.list(), config.classes)
    if not rows:
        return 'idle'
    run_id = uuid4().hex
    bucket = store.client.storage.from_(BUCKET)
    base_dir = config.directories['models'] / 'semantic-v1'
    stage = 'seed'
    try:
        seed_meta = json.loads((base_dir / 'learning_seed.json').read_text())
        if not any(r.get('training_status') in ('queued', 'failed', 'training', 'validating', 'waiting_dataset')
                   or r.get('training_result', {}).get('seed_sha256') != seed_meta['sha256'] for r in rows):
            return 'idle'
        seed_bytes = (base_dir / 'learning_seed.npz').read_bytes()
        if hashlib.sha256(seed_bytes).hexdigest() != seed_meta['sha256']:
            raise ValueError('Seed integrity mismatch')
        base = SemanticOnnxClassifier(base_dir / 'semantic.json')
        if (seed_meta['processing'] != processing_contract(config)
                or seed_meta['encoder_sha256'] != base.metadata['encoder_sha256']):
            raise ValueError('Seed preparation or encoder mismatch')
        with np.load(io.BytesIO(seed_bytes), allow_pickle=False) as data:
            train_x, train_y = data['train_x'], data['train_y'].tolist()
            val_x, val_y = data['validation_x'], data['validation_y'].tolist()
        update_rows(store, rows, 'training', run_id)
        print(f'Neural batch {run_id}: {len(rows)} approved contributions', flush=True)
        with TemporaryDirectory(prefix='recicla-neural-') as temporary:
            stage = 'reference'
            folder = Path(temporary)
            reference = base
            if any(x.get('name') == 'semantic_active.json' for x in bucket.list()):
                active = json.loads(bucket.download('semantic_active.json'))
                # A revoked review invalidates the previous adapted model.
                current = {r['id']: r for r in store.list()}
                valid = all(current.get(k, {}).get('status') == 'approved'
                            and current[k].get('consent') is True
                            and current[k].get('reviewed_at') == v['reviewed_at']
                            and current[k].get('expected_class') == v['expected_class']
                            for k, v in active['reviews'].items())
                if valid:
                    from ecoscan.services.semantic_release import materialize
                    path = materialize(bucket, active, folder / 'reference', config)
                    reference = SemanticOnnxClassifier(path, base_dir)
            new_features, seen = [], {}
            stage = 'photos'
            # Segmentation is explanatory, not applied to this encoder's RGB input.
            options = replace(default_processing_options(config), segmentation_name='none', morphology_name='none')
            for index, row in enumerate(rows):
                data = store.image(row)
                digest = hashlib.sha256(data).hexdigest()
                if digest in seed_meta['validation_hashes'] + seed_meta.get('held_out_hashes', []):
                    raise ValueError('Approved image overlaps validation')
                if digest in seen:
                    if seen[digest] != row['expected_class']:
                        raise ValueError('Conflicting labels for duplicate photo')
                    continue
                seen[digest] = row['expected_class']
                path = folder / 'photo.jpg'
                path.write_bytes(data)
                image = run_processing_pipeline(path, config, options).recognition_image
                new_features.append(base.image_features(image))
                train_y.append(row['expected_class'])
                print(f'Prepared contribution {index + 1}/{len(rows)}', flush=True)
            train_x = np.vstack([train_x, *[f[None] for f in new_features]])
            stage = 'fit'
            print('Fitting neural classification head', flush=True)
            arrays, head_classes = fit_head(base, train_x, train_y)
            base.arrays = arrays
            base.metadata = {**base.metadata, 'head_classes': head_classes}
            # Keep the reference separate when it is the bundled baseline.
            if reference is base:
                reference = SemanticOnnxClassifier(base_dir / 'semantic.json')
            update_rows(store, rows, 'validating', run_id)
            stage = 'validation'
            print('Comparing candidate with active model', flush=True)
            candidate_metrics = evaluate(base, val_x, val_y, config.classes)
            reference_metrics = evaluate(reference, val_x, val_y, config.classes)
            passed = (improvement(candidate_metrics, reference_metrics, config.classes)
                      and candidate_metrics['wrong_confident'] <= reference_metrics['wrong_confident'])
            latest = {r['id']: r for r in store.list()}
            if any(latest.get(r['id'], {}).get('revision') != r['revision'] for r in rows):
                raise ValueError('Review changed during training')
            buffer = io.BytesIO()
            np.savez_compressed(buffer, **arrays)
            head_bytes = buffer.getvalue()
            metadata = {**base.metadata, 'head_sha256': hashlib.sha256(head_bytes).hexdigest()}
            meta_bytes = json.dumps(metadata).encode()
            prefix = f'runs/{run_id}'
            stage = 'artifacts'
            for name, data in [('head.npz', head_bytes), ('semantic.json', meta_bytes),
                               ('metrics.json', json.dumps({'candidate': candidate_metrics,
                                'reference': reference_metrics, 'assisted_only': True,
                                'validation_kind': 'historical_reused'}).encode())]:
                bucket.upload(f'{prefix}/{name}', data, file_options={'content-type': 'application/octet-stream'})
            if passed:
                stage = 'publication'
                release = {'id': run_id, 'metadata_sha256': hashlib.sha256(meta_bytes).hexdigest(),
                           'reviews': {r['id']: {'reviewed_at': r.get('reviewed_at'),
                                               'expected_class': r['expected_class']} for r in rows}}
                bucket.upload('semantic_active.json', json.dumps(release).encode(),
                              file_options={'upsert': 'true', 'content-type': 'application/json'})
            state = 'published' if passed else 'validation_failed'
            outcome = {**evaluation_details(candidate_metrics, reference_metrics, config.classes, train_y),
                       'candidate_macro_f1': candidate_metrics['macro_f1'],
                       'seed_sha256': seed_meta['sha256'],
                       'reference_macro_f1': reference_metrics['macro_f1'],
                       'published': passed,
                       'reason': 'improved' if passed else 'improvement_gate_not_met'}
            print('Neural evaluation: ' + json.dumps(outcome), flush=True)
            for row in rows:
                row['training_result'] = outcome
            update_rows(store, rows, state, run_id)
            return state
    except Exception:
        try:
            update_rows(store, rows, 'failed', run_id)
        except Exception:
            pass
        raise RuntimeError(f'Neural learning failed at stage: {stage}.') from None
