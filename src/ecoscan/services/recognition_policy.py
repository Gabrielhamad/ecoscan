"""Reviewed per-class opt-in, bound to private external evidence and exact artifacts."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

from ecoscan.config import AppConfig

LABELS = {'metal': 'METAL', 'plastic': 'PLÁSTICO', 'glass': 'VIDRO',
          'paper_cardboard': 'PAPEL E PAPELÃO', 'battery': 'PILHAS E BATERIAS', 'electronic': 'ELETRÔNICOS'}
HASH = re.compile(r'[0-9a-f]{64}\Z')
TOKEN = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}\Z')
ENGINE_VERSION = 'recognition-decision-v1'


def decision_code_sha256() -> str:
    """Bind approvals to the actual producer, scoring and preparation implementation."""
    package = Path(__file__).resolve().parent.parent
    names = ('services/recognition_policy.py', 'services/recognition_safety.py', 'services/analysis_service.py',
             'classification/semantic_onnx.py', 'app/pipeline.py', 'app/processing_options.py')
    paths = [package / name for name in names] + sorted((package / 'image_processing').glob('*.py'))
    payload = {p.relative_to(package).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def unit_score(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1 and math.isfinite(value)


@dataclass(frozen=True)
class ClassDecisionPolicy:
    assertive: bool = False
    threshold: float = 1.0
    min_margin: float = 1.0
    max_unknown_score: float = 0.0
    temperature: float = 1.0
    evidence_sha256: str = ''
    artifact_hashes: tuple[str, str, str, str] = ('', '', '', '')
    evidence_valid: bool = False
    gate_reason: str = 'assertiveness_disabled'


@dataclass(frozen=True)
class DecisionPolicy:
    version: str = 'fallback-disabled-v1'
    sha256: str = 'unavailable'
    classes: dict[str, ClassDecisionPolicy] = field(default_factory=lambda: {c: ClassDecisionPolicy() for c in LABELS})
    reason: str = 'policy_unavailable'
    engine_sha256: str = ''


def _read_reference(config: AppConfig, reference: dict[str, Any]) -> tuple[dict[str, Any], str]:
    name, digest = reference['path'], reference['sha256']
    if not isinstance(name, str) or not isinstance(digest, str) or not HASH.fullmatch(digest):
        raise ValueError('Invalid evidence reference')
    relative = Path(name)
    root = config.project_root.resolve() / 'reports' / 'recognition_evidence'
    if root.resolve() != root:
        raise ValueError('Evidence directory must not escape through a symlink')
    path = (config.project_root / relative).resolve()
    if relative.is_absolute() or '..' in relative.parts or not path.is_relative_to(root):
        raise ValueError('Evidence must remain in the private evidence directory')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('Evidence checksum mismatch')
    payload = json.loads(data)
    if not isinstance(payload, dict):
        raise ValueError('Invalid evidence document')
    return payload, digest


def _hashes(payload: dict[str, Any]) -> tuple[str, str, str, str]:
    values = tuple(payload[k] for k in ('model_metadata_sha256', 'encoder_sha256', 'head_sha256', 'processing_sha256'))
    if any(not isinstance(v, str) or not HASH.fullmatch(v) for v in values):
        raise ValueError('Missing artifact binding')
    return values


def _class_rule(config: AppConfig, class_id: str, raw: dict[str, Any], requirements: dict[str, Any],
                policy_version: str, engine_sha256: str) -> ClassDecisionPolicy:
    if raw.get('assertive') is not True:
        return ClassDecisionPolicy()
    try:
        threshold, margin, maximum = (raw[k] for k in ('threshold', 'min_margin', 'max_unknown_score'))
        if not all(unit_score(v) for v in (threshold, margin, maximum)) or threshold <= 0 or margin <= 0:
            raise ValueError('Unconfigured decision thresholds')
        gate, gate_sha = _read_reference(config, raw['evidence'])
        if (gate.get('schema_version') != 1 or gate.get('class_id') != class_id
                or gate.get('policy_version') != policy_version or gate.get('engine_version') != ENGINE_VERSION
                or gate.get('engine_sha256') != engine_sha256
                or gate.get('approved') is not True or not TOKEN.fullmatch(gate.get('approval_reference', ''))):
            raise ValueError('Missing independent gate approval')
        report, _ = _read_reference(config, gate['evaluation'])
        calibration, calibration_sha = _read_reference(config, gate['calibration'])
        audit, _ = _read_reference(config, gate['source_audit'])
        manifest = report['integrity']['manifest_sha256']
        if not isinstance(manifest, str) or not HASH.fullmatch(manifest):
            raise ValueError('Invalid evaluation manifest binding')
        if (audit.get('approved') is not True or audit.get('independence_reviewed') is not True
                or audit.get('object_session_splits_reviewed') is not True or audit.get('consent_reviewed') is not True
                or audit.get('decision_rule_reviewed') is not True
                or audit.get('evaluation_manifest_sha256') != manifest
                or audit.get('calibration_manifest_sha256') != calibration.get('manifest_sha256')
                or not TOKEN.fullmatch(audit.get('reviewer_id', ''))):
            raise ValueError('External source audit absent')
        # The measured report remains independent_test=false; external approval is a separate document.
        if report.get('source_kind') != 'field_photo' or report.get('independent_test') is not False:
            raise ValueError('Only real field reports can support opt-in')
        counts = report['counts'][class_id]
        accepted = report['accepted']['by_class'][class_id]
        recall = report['top1']['by_class'][class_id]['recall']
        support = (counts['objects'], counts['sessions'], report['counts']['unknown']['objects'],
                   calibration['objects'], calibration['sessions'])
        if (any(type(v) is not int or v < 0 for v in support)
                or counts['objects'] < requirements['minimum_objects'] or counts['sessions'] < requirements['minimum_sessions']
                or report['counts']['unknown']['objects'] < requirements['minimum_unknown_objects']
                or not unit_score(accepted['precision']) or accepted['precision'] < requirements['minimum_precision']
                or not unit_score(recall) or recall < requirements['minimum_recall']):
            raise ValueError('Independent class evidence insufficient')
        measured = report['decision_evaluation'][class_id]
        numbers = (measured['reference_objects'], measured['identified_objects'], measured['correct_objects'])
        if (any(type(v) is not int or v < 0 for v in numbers)
                or measured['reference_objects'] != counts['objects']
                or measured['identified_objects'] < requirements['minimum_objects']
                or measured['correct_objects'] > min(measured['reference_objects'], measured['identified_objects'])
                or measured.get('calibration_sha256') != calibration_sha
                or measured.get('engine_sha256') != engine_sha256 or measured.get('policy_version') != policy_version
                or any(measured.get(k) != raw[k] for k in ('threshold', 'min_margin', 'max_unknown_score'))
                or measured.get('temperature') != calibration['temperature']
                or measured['correct_objects'] / measured['identified_objects'] < requirements['minimum_precision']
                or measured['correct_objects'] / measured['reference_objects'] < requirements['minimum_recall']):
            raise ValueError('Independent evaluation must cover this exact decision rule')
        bound = _hashes(report['integrity'])
        if (calibration.get('class_id') != class_id or calibration.get('method') != 'temperature_scaling'
                or calibration.get('split') != 'validation' or calibration.get('held_out') is not True
                or calibration.get('manifest_sha256') == manifest or not HASH.fullmatch(calibration.get('manifest_sha256', ''))
                or _hashes(calibration['integrity']) != bound
                or calibration.get('threshold') != threshold or calibration.get('min_margin') != margin
                or calibration.get('max_unknown_score') != maximum
                or calibration['objects'] < requirements['minimum_objects']
                or calibration['sessions'] < requirements['minimum_sessions']
                or not unit_score(calibration['ece']) or calibration['ece'] > requirements['maximum_ece']):
            raise ValueError('Calibration is not independently bound to this rule')
        temperature = calibration['temperature']
        if isinstance(temperature, bool) or not isinstance(temperature, (float, int)) or not .1 <= temperature <= 10 or not math.isfinite(temperature):
            raise ValueError('Invalid calibrated temperature')
        return ClassDecisionPolicy(True, threshold, margin, maximum, temperature, gate_sha, bound, True, 'independent_gate_verified')
    except (ValueError, TypeError, KeyError, OSError, AttributeError):
        return ClassDecisionPolicy(assertive=True, gate_reason='evidence_invalid_or_unavailable')


def load_decision_policy(config: AppConfig) -> DecisionPolicy:
    try:
        name = config.model.get('decision_policy_path', 'config/recognition_policy.json')
        path = (config.project_root / name).resolve()
        if not path.is_relative_to((config.project_root / 'config').resolve()):
            raise ValueError('Invalid policy location')
        data = path.read_bytes()
        payload = json.loads(data)
        if payload.get('schema_version') != 1 or not TOKEN.fullmatch(payload.get('version', '')) or set(payload['classes']) != set(LABELS):
            raise ValueError('Invalid policy schema')
        requirements = payload['evidence_requirements']
        if (type(requirements['minimum_objects']) is not int or requirements['minimum_objects'] < 30
                or type(requirements['minimum_sessions']) is not int or requirements['minimum_sessions'] < 3
                or type(requirements['minimum_unknown_objects']) is not int or requirements['minimum_unknown_objects'] < 10
                or not unit_score(requirements['minimum_precision']) or requirements['minimum_precision'] < .95
                or not unit_score(requirements['minimum_recall']) or requirements['minimum_recall'] < .8
                or not unit_score(requirements['maximum_ece']) or requirements['maximum_ece'] > .1):
            raise ValueError('Evidence requirements below reviewed floor')
        engine_sha = decision_code_sha256()
        rules = {c: _class_rule(config, c, payload['classes'][c], requirements, payload['version'], engine_sha) for c in LABELS}
        return DecisionPolicy(payload['version'], hashlib.sha256(data).hexdigest(), rules, '', engine_sha)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return DecisionPolicy()
