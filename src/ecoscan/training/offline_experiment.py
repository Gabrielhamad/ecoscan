"""Two-phase local experiment: validation freeze, then a single locked final test.

There is deliberately no release publication or runtime-compatible export command.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

import numpy as np

from ecoscan.classification.semantic_onnx import SemanticOnnxClassifier, file_digest
from ecoscan.config import AppConfig
from ecoscan.training.offline_data import (
    AUGMENTATIONS, TOKEN, EmbeddingCache, audit_inputs, code_digest, digest_json, versions, verify_images, write_json,
)
from ecoscan.training.offline_candidates import (
    REGULARIZATION, SEED, calibrate, evaluate_candidate, fit_candidate, gate, head_model, validation_partition,
)

DEFAULT_POLICY = {'macro_f1_gain': .005, 'max_recall_drop': 0.0, 'minimum_objects_per_class': 10,
                  'minimum_sessions_per_class': 2, 'minimum_accepted_precision': .95,
                  'minimum_accepted': 10, 'max_coverage_drop': 0.0,
                  'max_head_latency_ratio': 1.25, 'head_latency_allowance_ms': 1.0}


def _peak_rss_linux() -> int | None:
    if sys.platform != 'linux':
        return None
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def _root(config: AppConfig) -> Path:
    models = config.directories['models'].resolve()
    root = models / 'candidates'
    if root.resolve() != root:
        raise ValueError('Candidates directory must not be a symlink')
    root.mkdir(parents=True, exist_ok=True)
    return root


def _policy(path: Path) -> dict[str, Any]:
    policy = json.loads(path.read_text())
    # Initial agreement matches the existing F1 gain and forbids quality/coverage regressions.
    # Changing the policy requires a reviewed code change, not tuning on the final test.
    if policy != DEFAULT_POLICY:
        raise ValueError('Use the reviewed default policy; changes require a separate review')
    return policy


def _identity(config: AppConfig, model_path: Path, manifest: Path, audit: Path, policy: Path) -> dict[str, Any]:
    return {'manifest_sha256': file_digest(manifest), 'audit_sha256': file_digest(audit),
            'policy_sha256': file_digest(policy), 'baseline_metadata_sha256': file_digest(model_path),
            'baseline_head_sha256': file_digest(model_path.parent / 'head.npz'),
            'baseline_seed_metadata_sha256': file_digest(model_path.parent / 'learning_seed.json'),
            'encoder_license_sha256': file_digest(model_path.parent / 'LICENSE-CLIP'),
            'code_sha256': code_digest(config), 'versions': versions(), 'seed': SEED}


def _export(folder: Path, name: str, model: SemanticOnnxClassifier, rule: dict[str, Any]) -> dict[str, Any]:
    weights = folder / (name + '.npz')
    with weights.open('xb') as file:
        np.savez_compressed(file, **model.arrays)
    metadata = {**model.metadata, 'head_sha256': file_digest(weights)}
    candidate = folder / (name + '.candidate.json')
    write_json(candidate, {'format': 'ecoscan-offline-candidate-v1', 'semantic_metadata': metadata, 'rule': rule})
    return {'weights_file': weights.name, 'weights_sha256': file_digest(weights),
            'candidate_file': candidate.name, 'candidate_sha256': file_digest(candidate)}


def _load(folder: Path, item: dict[str, Any]) -> tuple[SemanticOnnxClassifier, dict[str, Any]]:
    for file_field, hash_field in (('weights_file', 'weights_sha256'), ('candidate_file', 'candidate_sha256')):
        name = item[file_field]
        if not isinstance(name, str) or Path(name).name != name or not (folder / name).resolve().is_relative_to(folder.resolve()):
            raise ValueError('Unsafe frozen artifact path')
        if file_digest(folder / name) != item[hash_field]:
            raise ValueError('Frozen artifact checksum mismatch')
    descriptor = json.loads((folder / item['candidate_file']).read_text())
    if descriptor['format'] != 'ecoscan-offline-candidate-v1':
        raise ValueError('Invalid offline candidate format')
    with np.load(folder / item['weights_file'], allow_pickle=False) as data:
        arrays = {key: data[key].copy() for key in data.files}
    if not all(np.isfinite(value).all() for value in arrays.values()):
        raise ValueError('Invalid frozen arrays')
    return head_model(arrays, descriptor['semantic_metadata']), descriptor['rule']


def _report(folder: Path, stage: str, result: dict[str, Any]) -> None:
    write_json(folder / (stage + '.json'), result)
    with (folder / (stage + '.md')).open('x', encoding='utf-8') as file:
        file.write('# Experimento offline — ' + stage + '\n\n')
        file.write('Decisão: ' + result['decision'] + '. Artefato ativo preservado; independent_test=false.\n\n')
        file.write('Dados de origem dependem de auditoria externa. Fixtures de testes não medem campo.\n\n')
        file.write('Macro F1 usa a taxonomia completa da release, inclusive unknown.\n\n')
        file.write('| Modelo | Macro F1 | Precisão aceita | Cobertura | Erros aceitos | ms/cabeça/imagem | Gate |\n')
        file.write('| --- | --- | --- | --- | --- | --- | --- |\n')
        for name, metrics in result['metrics'].items():
            reason = ', '.join(result.get('gates', {}).get(name, [])) or 'ver JSON'
            file.write(f"| {name} | {metrics['top1']['macro_f1']:.6f} | {metrics['accepted_precision']} | "
                       f"{metrics['coverage']:.6f} | {metrics['wrong_accepted']} | {metrics['head_ms_per_image']:.6f} | {reason} |\n")
        file.write('\nRecall por classe, suporte original, confusões e matrizes completos no JSON irmão.\n')


def fit_experiment(config: AppConfig, manifest: Path, audit: Path, policy_path: Path,
                   source: Path, run_name: str) -> dict[str, Any]:
    if not TOKEN.fullmatch(run_name):
        raise ValueError('Use an opaque run name')
    policy = _policy(policy_path)
    model_path = config.directories['models'] / 'semantic-v1' / 'semantic.json'
    metadata = json.loads(model_path.read_text())
    rows, receipt = audit_inputs(manifest, audit, policy_path, metadata['classes'])
    history = json.loads((model_path.parent / 'learning_seed.json').read_text())
    known = set(history.get('training_hashes', []) + history.get('validation_hashes', []) + history.get('held_out_hashes', []))
    if any(r['sha256'] in known for r in rows if r['split'] != 'train'):
        raise ValueError('Validation/test photos overlap known historical development images')
    identity = _identity(config, model_path, manifest, audit, policy_path)
    development = [r for r in rows if r['split'] != 'test']
    verify_images(source, development, config)  # Never open/encode test photos here.
    folder = _root(config) / run_name
    folder.mkdir(exist_ok=False)
    started = perf_counter()
    base = SemanticOnnxClassifier(model_path)
    load_ms = (perf_counter() - started) * 1000
    cache = EmbeddingCache(_root(config) / 'cache', base, config)
    training = [r for r in development if r['split'] == 'train']
    validation = [r for r in development if r['split'] == 'validation']
    if not training or not validation:
        raise ValueError('Missing train or validation photos')
    cal, selection = validation_partition(validation, policy['minimum_objects_per_class'])
    x_val = np.array([cache.feature(source, r) for r in validation])
    selection_rows = [validation[i] for i in selection]
    nominal = {'temperature': 1.0, 'thresholds': {c: metadata['threshold'] for c in base.classes if c != 'unknown'}}
    metrics = {'baseline': evaluate_candidate(base, x_val[selection], selection_rows, nominal)}
    exported = {'baseline': _export(folder, 'baseline', base, nominal)}
    gates = {}
    if cal:
        rule = calibrate(base, x_val[cal], [validation[i] for i in cal], policy['minimum_objects_per_class'])
        metrics['baseline-calibrated'] = evaluate_candidate(base, x_val[selection], selection_rows, rule)
        gates['baseline-calibrated'] = gate(metrics['baseline-calibrated'], metrics['baseline'], policy)
        exported['baseline-calibrated'] = _export(folder, 'baseline-calibrated', base, rule)
    for augmented in (False, True):
        x, y = [], []
        for row in training:
            for augmentation in (list(AUGMENTATIONS) if augmented else ['none']):
                x.append(cache.feature(source, row, augmentation))
                y.append(row['class_id'])
        for balanced in (False, True):
            for c in REGULARIZATION:
                name = f"lr-c{c}-{'balanced' if balanced else 'regular'}-{'exposure' if augmented else 'original'}"
                model = fit_candidate(base, np.array(x), y, c, balanced)
                rules = {'raw': nominal}
                if cal:
                    rules['calibrated'] = calibrate(model, x_val[cal], [validation[i] for i in cal], policy['minimum_objects_per_class'])
                for suffix, rule in rules.items():
                    identifier = name + '-' + suffix
                    metrics[identifier] = evaluate_candidate(model, x_val[selection], selection_rows, rule)
                    gates[identifier] = gate(metrics[identifier], metrics['baseline'], policy)
                    exported[identifier] = _export(folder, identifier, model, rule)
    eligible = [name for name, reasons in gates.items() if not reasons]
    selected = min(eligible, key=lambda name: (-metrics[name]['top1']['macro_f1'],
                                             -(metrics[name]['accepted_precision'] or 0.0), -metrics[name]['coverage'], name)) if eligible else None
    verify_images(source, development, config)
    if identity != _identity(config, model_path, manifest, audit, policy_path):
        raise ValueError('Inputs changed during experiment')
    freeze = {'format': 'ecoscan-offline-freeze-v1', 'identity': identity, 'policy': policy,
              'models': exported, 'selected': selected, 'validation_gate_passed': selected is not None,
              'test_identity': digest_json(sorted(r['rgb_sha256'] for r in rows if r['split'] == 'test')),
              'processing': metadata['processing'], 'encoder_sha256': metadata['encoder_sha256'],
              'licenses': sorted({r['license'] for r in rows}), 'scope': receipt['scope'],
              'source_kind': rows[0]['source_kind'], 'independent_test': False}
    write_json(folder / 'freeze.json', freeze)
    write_json(folder / 'freeze.checksum.json', {'sha256': file_digest(folder / 'freeze.json')})
    result = {'decision': 'FROZEN_FOR_SINGLE_TEST' if selected else 'NO-GO', 'selected': selected,
              'metrics': metrics, 'gates': gates, 'identity': identity, 'independent_test': False,
              'source_kind': rows[0]['source_kind'], 'test_opened': False,
              'calibration': 'held_out_validation_groups' if cal else 'not_run_insufficient_group_support',
              'train_original_images': len(training), 'train_original_objects': len({r['object_id'] for r in training}),
              'augmented_rows_per_original': len(AUGMENTATIONS), 'validation_selection_indices': selection,
              'validation_calibration_indices': cal, 'encoder_load_ms': load_ms,
              'process_peak_rss_kib_linux': _peak_rss_linux(),
              'latency_scope': 'Shared frozen encoder; head timings on cached selection embeddings; not end-to-end phone latency'}
    _report(folder, 'validation', result)
    return result


def final_test(config: AppConfig, manifest: Path, audit: Path, policy_path: Path,
               source: Path, run_name: str) -> dict[str, Any]:
    if not TOKEN.fullmatch(run_name):
        raise ValueError('Invalid run name')
    root, folder = _root(config), _root(config) / run_name
    if not folder.resolve().is_relative_to(root):
        raise ValueError('Frozen run escapes candidates directory')
    freeze_path = folder / 'freeze.json'
    if file_digest(freeze_path) != json.loads((folder / 'freeze.checksum.json').read_text())['sha256']:
        raise ValueError('Freeze checksum mismatch')
    freeze = json.loads(freeze_path.read_text())
    model_path = config.directories['models'] / 'semantic-v1' / 'semantic.json'
    if freeze['identity'] != _identity(config, model_path, manifest, audit, policy_path) or freeze['policy'] != _policy(policy_path):
        raise ValueError('Frozen data, code, environment, policy or baseline changed')
    rows, _ = audit_inputs(manifest, audit, policy_path, json.loads(model_path.read_text())['classes'])
    if not freeze['validation_gate_passed'] or freeze['selected'] is None:
        raise ValueError('NO-GO on validation; do not consume the final test')
    selected = freeze['selected']
    frozen_models = {name: _load(folder, freeze['models'][name]) for name in ('baseline', selected)}
    ledger = root / 'test-ledger'
    ledger.mkdir(exist_ok=True)
    marker = ledger / (freeze['test_identity'] + '.json')
    # Exclusive reservation precedes even image inspection; failures consume this holdout too.
    write_json(marker, {'state': 'consumed', 'freeze_sha256': file_digest(freeze_path),
                        'reserved_at_utc': datetime.now(timezone.utc).isoformat(), 'independent_test': False})
    test = [r for r in rows if r['split'] == 'test']
    used = ledger / 'used-images'
    used.mkdir(exist_ok=True)
    for row in sorted(test, key=lambda r: r['rgb_sha256']):
        write_json(used / (row['rgb_sha256'] + '.json'), {'state': 'consumed', 'test_identity': freeze['test_identity']})
    verify_images(source, test, config)
    base = SemanticOnnxClassifier(model_path)
    cache = EmbeddingCache(root / 'cache', base, config)
    started = perf_counter()
    x = np.array([cache.feature(source, row) for row in test])
    embedding_ms = (perf_counter() - started) * 1000
    metrics = {name: evaluate_candidate(model, x, test, rule) for name, (model, rule) in frozen_models.items()}
    reasons = gate(metrics[selected], metrics['baseline'], freeze['policy'])
    verify_images(source, test, config)
    if freeze['identity'] != _identity(config, model_path, manifest, audit, policy_path):
        raise ValueError('Frozen inputs changed during final test')
    result = {'decision': 'ELIGIBLE_FOR_REVIEW' if not reasons else 'NO-GO',
              'selected': selected, 'gates': {selected: reasons}, 'metrics': metrics,
              'identity': freeze['identity'], 'freeze_sha256': file_digest(freeze_path),
              'independent_test': False, 'source_kind': freeze['source_kind'], 'published': False,
              'test_original_images': len(test), 'test_original_objects': len({r['object_id'] for r in test}),
              'embedding_wall_ms': embedding_ms, 'embedding_time_includes_cache_io': True}
    _report(folder, 'final', result)
    return result
