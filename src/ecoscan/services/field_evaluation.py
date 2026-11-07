"""Offline field reports using the existing pipeline and semantic ONNX classifier."""
from __future__ import annotations

import csv
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import subprocess
from time import perf_counter
from typing import Any, Collection

import numpy as np

from ecoscan.app.pipeline import default_processing_options, run_processing_pipeline
from ecoscan.classification.semantic_onnx import SemanticOnnxClassifier
from ecoscan.config import AppConfig
from ecoscan.image_processing.contracts import processing_contract
from ecoscan.metrics.classification_metrics import classification_report
from ecoscan.services.evaluation_manifest import SCENARIOS, audit_evaluation_manifest, verify_local_images
from ecoscan.services.processing_evidence import array_digest


def _classification(rows: list[dict[str, Any]], classes: list[str], prediction_key: str) -> dict[str, Any]:
    report = classification_report([r['expected'] for r in rows], [r[prediction_key] for r in rows], classes)
    # Keep all predicted materials in the matrix, but do not average untested classes as zeros.
    supported = [v for v in report['by_class'].values() if v['support']]
    for name in ('precision', 'recall', 'f1'):
        report['macro_' + name] = sum(v[name] for v in supported) / len(supported)
    report['macro_scope'] = 'classes with reference support > 0, including unknown if present'
    return report


def _coverage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [r for r in rows if r['accepted_class'] is not None]
    correct = sum(r['accepted_class'] == r['expected'] for r in accepted)
    return {'accepted': len(accepted), 'correct': correct, 'wrong': len(accepted) - correct,
            'rejected': len(rows) - len(accepted), 'coverage': len(accepted) / len(rows),
            'selective_error_rate': (len(accepted) - correct) / len(accepted) if accepted else None}


def summarize_predictions(rows: list[dict[str, Any]], classes: list[str], threshold: float) -> dict[str, Any]:
    """Image-weighted metrics before human confirmation; no threshold is selected here."""
    if not rows:
        raise ValueError('No test predictions')
    counts = {}
    for label in classes:
        subset = [r for r in rows if r['expected'] == label]
        negatives = sum(r['expected'] != label for r in rows)
        fp = sum(r['expected'] != label and r['top_class_id'] == label for r in rows)
        accepted_fp = sum(r['expected'] != label and r['accepted_class'] == label for r in rows)
        counts[label] = {'images': len(subset), 'objects': len({r['object_id'] for r in subset}),
                         'sessions': len({r['session_id'] for r in subset}),
                         'rejected': sum(r['accepted_class'] is None for r in subset),
                         'false_positives_top1': fp, 'false_positives_accepted': accepted_fp,
                         'negative_support': negatives,
                         'false_positive_rate_top1': fp / negatives if negatives else None,
                         'false_positive_rate_accepted': accepted_fp / negatives if negatives else None}
    curve = []
    for cutoff in sorted({0.0, .5, .6, .7, .8, .9, .95, 1.0, threshold}):
        counterfactual = [{**r, 'accepted_class': r['top_class_id']
                           if r['top_class_id'] != 'unknown' and r['score'] >= cutoff else None} for r in rows]
        curve.append({'threshold': cutoff, **_coverage(counterfactual)})
    scenarios = {}
    for scenario in sorted(SCENARIOS):
        subset = [r for r in rows if r['scenario'] == scenario]
        scenarios[scenario] = {'images': len(subset),
                               'top1': _classification(subset, classes, 'top_class_id') if subset else None,
                               'acceptance': _coverage(subset) if subset else None}
    latency = {}
    for name in ('pipeline_ms', 'inference_ms', 'total_ms'):
        values = [r[name] for r in rows]
        latency[name] = {'min': min(values), 'p50': float(np.percentile(values, 50)),
                          'p95': float(np.percentile(values, 95)), 'max': max(values)}
    return {'counts': counts, 'top1': _classification(rows, classes, 'top_class_id'),
            'accepted': _classification(rows, classes, 'accepted_class'),
            'acceptance': {'threshold': threshold, **_coverage(rows)},
            'selectivity': curve, 'scenarios': scenarios, 'latency_ms': latency}


def _cases(path: Path | None, records: list[dict[str, Any]]) -> list[int]:
    if path is None:
        return []
    test = {r['path']: (i, r['class_id']) for i, r in enumerate(records) if r['split'] == 'test'}
    selected = []
    with path.open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != ['path', 'expected_class']:
            raise ValueError('Cases CSV requires path,expected_class')
        for row in reader:
            if row.get('path') not in test or test[row['path']][1] != row.get('expected_class'):
                raise ValueError('Cases must reference frozen test records with matching labels')
            index = test[row['path']][0]
            if index in selected:
                raise ValueError('Duplicate case')
            selected.append(index)
    return selected


def evaluate_field_manifest(config: AppConfig, model_path: Path, manifest_path: Path, source: Path,
                            *, development_hashes: Collection[str] = (), cases_path: Path | None = None) -> dict[str, Any]:
    manifest_bytes = manifest_path.read_bytes()
    records = json.loads(manifest_bytes)
    classes = [*config.classes, 'unknown']
    audit = audit_evaluation_manifest(records, allowed_classes=classes, require_provenance=True,
                                      development_hashes=development_hashes)
    verify_local_images(source, records, config)
    cases_bytes = cases_path.read_bytes() if cases_path else None
    cases = _cases(cases_path, records)
    metadata_bytes = model_path.read_bytes()
    metadata = json.loads(metadata_bytes)
    contract = processing_contract(config)
    if not isinstance(metadata, dict):
        raise ValueError('Invalid model metadata')
    declared = metadata.get('classes')
    if (metadata.get('processing') != contract or not isinstance(declared, list)
            or len(declared) != len(classes) or not all(isinstance(c, str) for c in declared)
            or set(declared) != set(classes)):
        raise ValueError('Model and evaluation processing/classes differ')
    threshold = metadata.get('threshold')
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError('Invalid artifact threshold')
    started = perf_counter()
    model = SemanticOnnxClassifier(model_path)
    load_ms = (perf_counter() - started) * 1000
    options = replace(default_processing_options(config), segmentation_name='none', morphology_name='none')
    predictions = []
    for index, row in enumerate(records):
        if row['split'] != 'test':
            continue
        # Recheck immediately before use as well as in preflight.
        verify_local_images(source, [row], config)
        start = perf_counter()
        pipeline = run_processing_pipeline(source / row['path'], config, options)
        prepared = perf_counter()
        if pipeline.metadata['recognition_preparation']['contract'] != contract:
            raise ValueError('Pipeline preparation changed')
        prediction = model.predict_image(pipeline.recognition_image)
        finished = perf_counter()
        if (prediction.top_class_id not in classes or not math.isfinite(prediction.probability)
                or not 0 <= prediction.probability <= 1):
            raise ValueError('Invalid classifier prediction')
        expected_acceptance = prediction.top_class_id != 'unknown' and prediction.probability >= metadata['threshold']
        if prediction.accepted != expected_acceptance or prediction.class_id != (prediction.top_class_id if expected_acceptance else None):
            raise ValueError('Classifier acceptance does not match artifact threshold')
        predictions.append({'record_index': index, 'sha256': row['sha256'], 'expected': row['class_id'],
                            'object_id': row['object_id'], 'session_id': row['session_id'],
                            'scenario': row['scenario'], 'top_class_id': prediction.top_class_id,
                            'score': prediction.probability, 'accepted_class': prediction.class_id,
                            'recognition_rgb_sha256': array_digest(pipeline.recognition_image),
                            'pipeline_ms': (prepared - start) * 1000,
                            'inference_ms': (finished - prepared) * 1000, 'total_ms': (finished - start) * 1000})
    # A file/config mutation during a run must not yield a completed frozen report.
    verify_local_images(source, records, config)
    if model_path.read_bytes() != metadata_bytes or manifest_path.read_bytes() != manifest_bytes:
        raise ValueError('Manifest or model metadata changed during evaluation')
    if cases_path and cases_path.read_bytes() != cases_bytes:
        raise ValueError('Cases changed during evaluation')
    try:
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=config.project_root,
                                      text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=config.project_root, text=True))
    except (OSError, subprocess.CalledProcessError):
        sha, dirty = 'unavailable', None
    report = {'schema_version': 3, 'independent_test': False, 'manifest_audit': audit,
              'source_kind': records[0]['source_kind'], 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'evaluation_classes': classes, 'git_sha': sha, 'git_dirty': dirty, 'python': platform.python_version(),
              'platform': platform.platform(),
              'runtime_versions': {name: version(name) for name in ('numpy', 'Pillow', 'opencv-python-headless', 'onnxruntime')},
              'integrity': {'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
                            'model_metadata_sha256': hashlib.sha256(metadata_bytes).hexdigest(),
                            'head_sha256': model.metadata['head_sha256'],
                            'encoder_sha256': model.metadata['encoder_sha256'],
                            'processing_sha256': contract['sha256'],
                            'cases_sha256': hashlib.sha256(cases_bytes).hexdigest() if cases_bytes is not None else None},
              'processing_contract': contract, 'model_load_ms': load_ms,
              'latency_scope': 'CPU; includes first inference; pipeline includes decode; preflight excluded; no device equivalence',
              **summarize_predictions(predictions, classes, metadata['threshold'])}
    # Reports need no paths, object identifiers, session identifiers, EXIF or license documents.
    report['predictions'] = [{k: v for k, v in r.items() if k not in {'object_id', 'session_id'}} for r in predictions]
    report['cases'] = [r for r in report['predictions'] if r['record_index'] in cases]
    return report


def report_paths(output: Path) -> dict[str, Path]:
    if output.suffix.lower() != '.json':
        raise ValueError('Output must have .json extension')
    return {'json': output, 'markdown': output.with_suffix('.md'), 'classes': output.with_suffix('.csv'),
            'predictions': output.with_suffix('.predictions.csv'), 'confusion': output.with_suffix('.confusion.csv'),
            'selectivity': output.with_suffix('.selectivity.csv'), 'summary': output.with_suffix('.summary.csv'),
            'scenarios': output.with_suffix('.scenarios.csv')}


def _table(columns: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        return 'n/a' if value is None else str(value).replace('|', '\\|').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(columns) + ' |', '| ' + ' | '.join(['---'] * len(columns)) + ' |',
                      *['| ' + ' | '.join(map(cell, row)) + ' |' for row in rows]])


def write_field_report(report: dict[str, Any], output: Path) -> None:
    paths = report_paths(output)
    if any(p.exists() for p in paths.values()):
        raise ValueError('Use a new report path; existing reports are never overwritten')
    class_rows = [{'class_id': c, **report['counts'][c], **report['top1']['by_class'][c]} for c in report['evaluation_classes']]
    scenario_rows = [{'scenario': s, 'images': r['images'],
                      'top1_accuracy': r['top1']['accuracy'] if r['top1'] else None,
                      'coverage': r['acceptance']['coverage'] if r['acceptance'] else None,
                      'selective_error_rate': r['acceptance']['selective_error_rate'] if r['acceptance'] else None}
                     for s, r in report['scenarios'].items()]
    summary = {'independent_test': False, 'source_kind': report['source_kind'], 'git_sha': report['git_sha'],
               'git_dirty': report['git_dirty'], 'macro_scope': report['top1']['macro_scope'],
               **{k: report['top1'][k] for k in ('accuracy', 'macro_precision', 'macro_recall', 'macro_f1')},
               **report['acceptance'], **report['integrity'], 'model_load_ms': report['model_load_ms'],
               **{stage + '_' + metric: value for stage, values in report['latency_ms'].items() for metric, value in values.items()}}
    markdown = (f"# Avaliação local — {report['source_kind']}\n\n"
                "independent_test=false. Declarações de origem não foram auditadas externamente.\n\n"
                "Fixtures sintéticas validam software; não representam resultados de campo.\n\n"
                f"Git: {report['git_sha']}; dirty={report['git_dirty']}. Métricas ponderadas por imagem, não por objeto.\n\n"
                f"Top-1: {report['top1']['accuracy']}; macro precisão/recall/F1: "
                f"{report['top1']['macro_precision']} / {report['top1']['macro_recall']} / {report['top1']['macro_f1']}.\n\n"
                f"Macro: {report['top1']['macro_scope']}. Classes sem suporte não estão validadas.\n\n"
                f"Decisão nominal do artefato: {report['acceptance']}.\n\n"
                + _table(['Classe', 'N imagens', 'N objetos', 'N sessões', 'Precisão', 'Recall', 'F1', 'Rejeições', 'FP top-1', 'FP aceitos'],
                         [[r[k] for k in ('class_id', 'images', 'objects', 'sessions', 'precision', 'recall', 'f1', 'rejected', 'false_positives_top1', 'false_positives_accepted')] for r in class_rows])
                + '\n\n## Cobertura e erro entre decisões aceitas\n\n'
                + _table(['Limiar', 'Aceitos', 'Cobertura', 'Taxa erros', 'Rejeitados'],
                         [[r[k] for k in ('threshold', 'accepted', 'coverage', 'selective_error_rate', 'rejected')] for r in report['selectivity']])
                + '\n\nCurva descritiva em limiares fixos; não usar o teste final para escolher parâmetros. Unknown nunca é aceito.\n\n'
                + '## Matriz top-1 (linha=real, coluna=predito)\n\n'
                + _table(['Real', *report['evaluation_classes']], [[c, *row] for c, row in zip(report['evaluation_classes'], report['top1']['confusion_matrix'], strict=True)])
                + '\n\n## Cenários\n\n'
                + _table(['Cenário', 'N', 'Top-1', 'Cobertura', 'Taxa erros aceitos'],
                         [list(r.values()) for r in scenario_rows])
                + '\n\n## Latência (ms)\n\n' + report['latency_scope'] + f"; carga do modelo={report['model_load_ms']}.\n\n"
                + _table(['Etapa', 'min', 'p50', 'p95', 'max'], [[s, *r.values()] for s, r in report['latency_ms'].items()])
                + '\n\n## Integridade\n\n' + _table(['Artefato', 'SHA-256'], [[k, v] for k, v in report['integrity'].items()])
                + '\n\nSem auditoria de dados históricos inacessíveis. Repetições do mesmo objeto/sessão são correlacionadas. A confirmação humana não entra nestas métricas.\n')
    output.parent.mkdir(parents=True, exist_ok=True)
    written = []
    try:
        for name, path in paths.items():
            with path.open('x', encoding='utf-8', newline='') as file:
                written.append(path)
                if name == 'json':
                    file.write(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
                elif name == 'markdown':
                    file.write(markdown)
                elif name == 'confusion':
                    writer = csv.writer(file)
                    writer.writerow(['true/predicted', *report['evaluation_classes']])
                    writer.writerows([[c, *row] for c, row in zip(report['evaluation_classes'], report['top1']['confusion_matrix'], strict=True)])
                else:
                    rows = {'classes': class_rows, 'predictions': report['predictions'], 'selectivity': report['selectivity'],
                            'scenarios': scenario_rows, 'summary': [{'metric': k, 'value': v} for k, v in summary.items()]}[name]
                    writer = csv.DictWriter(file, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        raise
