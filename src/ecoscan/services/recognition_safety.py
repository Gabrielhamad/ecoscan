"""UI-independent recognition decisions. A visual identification never authorizes disposal."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import logging
import math
from threading import Lock
from typing import Any, Literal

from ecoscan.config import AppConfig
from ecoscan.services.recognition_policy import DecisionPolicy, ENGINE_VERSION, HASH, LABELS, load_decision_policy, unit_score

DecisionState = Literal['identified', 'probable', 'unrecognized', 'out_of_scope', 'retake', 'model_unavailable']
LOGGER = logging.getLogger(__name__)
_COUNTS: Counter[str] = Counter()
_LOCK = Lock()


@dataclass(frozen=True)
class RecognitionInput:
    top_class: str | None = None
    probabilities: dict[str, float] = field(default_factory=dict)
    probability: float | None = None
    artifact_accepted: bool = False
    artifact_threshold: float | None = None
    capture_status: str = 'unknown'
    model_available: bool = True
    processing_compatible: bool = True
    outside_scope: bool = False
    model_type: str = 'semantic_onnx_assisted'
    model_sha256: str = ''
    encoder_sha256: str = ''
    head_sha256: str = ''
    processing_sha256: str = ''


@dataclass(frozen=True)
class RecognitionSafetyDecision:
    status: DecisionState
    tone: str
    title: str
    message: str
    primary_action: str
    allow_disposal_guidance: bool = False
    encourage_feedback: bool = True
    suggested_class: str | None = None
    can_correct: bool = True
    requires_confirmation: bool = True
    decision_reason: tuple[str, ...] = ()
    policy_version: str = 'fallback-disabled-v1'
    policy_sha256: str = 'unavailable'
    model_sha256: str = ''
    processing_sha256: str = ''
    evidence_sha256: str = ''
    engine_version: str = ENGINE_VERSION
    engine_sha256: str = ''


def decide_recognition(data: RecognitionInput, policy: DecisionPolicy | None = None) -> RecognitionSafetyDecision:
    policy = policy or DecisionPolicy()
    def output(status: DecisionState, title: str, reason: tuple[str, ...], suggested: str | None = None,
               evidence: str = '') -> RecognitionSafetyDecision:
        action = 'Confirme ou corrija o material na lista antes de consultar a destinação.'
        message = 'A foto não confirma composição, limpeza, conteúdo ou contaminação.'
        if status in {'probable', 'identified'}:
            message = 'Confirme para descartar. ' + message
        if suggested in {'battery', 'electronic'}:
            message = 'Coleta especial: confirme o item antes da destinação. ' + message
        if status == 'retake':
            action = 'Refaça a foto com luz e foco ou escolha o material manualmente.'
        elif status == 'model_unavailable':
            action = 'Escolha o material manualmente ou tente a análise novamente.'
        return RecognitionSafetyDecision(status, 'ok' if status == 'identified' else 'danger' if status == 'retake' else 'warn',
                                         title, message, action, suggested_class=suggested,
                                         decision_reason=reason, policy_version=policy.version,
                                         policy_sha256=policy.sha256, model_sha256=data.model_sha256,
                                         processing_sha256=data.processing_sha256, evidence_sha256=evidence,
                                         engine_sha256=policy.engine_sha256)
    if not data.model_available or not data.processing_compatible or data.model_type != 'semantic_onnx_assisted':
        return output('model_unavailable', 'Reconhecimento indisponível',
                      ('artifact_incompatible' if not data.processing_compatible else 'model_unavailable',))
    if data.capture_status == 'retake':
        return output('retake', 'Refaça a foto', ('capture_retake',))
    if data.outside_scope or data.top_class == 'unknown':
        return output('out_of_scope', 'Item fora do escopo', ('outside_scope',))
    scores = data.probabilities
    if (not isinstance(data.top_class, str) or data.top_class not in LABELS or not isinstance(scores, dict) or set(scores) != {*LABELS, 'unknown'}
            or not all(unit_score(v) for v in scores.values()) or not math.isclose(sum(scores.values()), 1, abs_tol=1e-5)
            or not unit_score(data.probability) or not math.isclose(scores.get(data.top_class, -1), data.probability, abs_tol=1e-5)):
        return output('unrecognized', 'Não foi possível reconhecer o material', ('invalid_or_missing_prediction',))
    top = data.top_class
    ranked = sorted(scores.values(), reverse=True)
    if scores[top] != ranked[0] or ranked[0] <= ranked[1]:
        return output('unrecognized', 'Sem correspondência visual suficiente', ('ambiguous_or_inconsistent_top_class',))
    reasons = []
    rule = policy.classes.get(top)
    if data.capture_status != 'good':
        reasons.append('capture_quality_not_verified_good')
    if top in {'battery', 'electronic'}:
        reasons.append('special_collection_confirmation')
    if rule is None or not rule.assertive or not rule.evidence_valid:
        reasons.append(rule.gate_reason if rule else 'class_policy_missing')
    else:
        actual_hashes = (data.model_sha256, data.encoder_sha256, data.head_sha256, data.processing_sha256)
        if any(not isinstance(v, str) or not HASH.fullmatch(v) for v in actual_hashes) or actual_hashes != rule.artifact_hashes:
            reasons.append('evidence_artifact_mismatch')
        if data.artifact_accepted is not True or not unit_score(data.artifact_threshold) or scores[top] < data.artifact_threshold:
            reasons.append('artifact_rejected')
        # Temperature acts on the entire score vector; raw score is not a probability of correctness.
        logits = {c: math.log(max(v, 1e-12)) / rule.temperature for c, v in scores.items()}
        maximum = max(logits.values())
        exponentials = {c: math.exp(v - maximum) for c, v in logits.items()}
        denominator = sum(exponentials.values())
        calibrated = scores if rule.temperature == 1.0 else {c: v / denominator for c, v in exponentials.items()}
        ordered = sorted(calibrated.values(), reverse=True)
        if calibrated[top] < rule.threshold:
            reasons.append('below_calibrated_threshold')
        if ordered[0] - ordered[1] < rule.min_margin:
            reasons.append('low_top_two_margin')
        if calibrated['unknown'] > rule.max_unknown_score:
            reasons.append('unknown_competitor')
    if policy.reason:
        reasons.append(policy.reason)
    if reasons:
        return output('probable', 'Melhor correspondência: ' + LABELS[top], tuple(reasons), top,
                      rule.evidence_sha256 if rule and rule.evidence_valid else '')
    return output('identified', 'Material identificado: ' + LABELS[top], ('independent_gate_passed',), top, rule.evidence_sha256)


def _capture_status(result: Any) -> str:
    metadata = getattr(getattr(result, 'pipeline', None), 'metadata', {})
    if not isinstance(metadata, dict):
        return 'unknown'
    capture = metadata.get('capture_quality') or {}
    status = capture.get('status', 'unknown') if isinstance(capture, dict) else 'unknown'
    if status == 'retake':
        return 'retake'
    metrics = metadata.get('quality') or {}
    quality = metrics.get('before_filter', {}) if isinstance(metrics, dict) else {}
    if isinstance(quality, dict) and (quality.get('exposure_status') in {'underexposed', 'overexposed'} or quality.get('focus_status') == 'low'):
        return 'retake'
    if not isinstance(quality, dict) or quality.get('exposure_status') != 'ok' or quality.get('focus_status') != 'ok':
        return 'unknown'
    return status if isinstance(status, str) and status in {'good', 'attention', 'retake'} else 'unknown'


def build_recognition_safety_decision(result: Any, *, action_confidence_threshold: float = .72,
                                      policy: DecisionPolicy | None = None) -> RecognitionSafetyDecision:
    # Legacy keyword remains validated, but never enables assertiveness.
    if not unit_score(action_confidence_threshold):
        raise ValueError('action_confidence_threshold must be finite and between 0 and 1')
    metadata = getattr(getattr(result, 'pipeline', None), 'metadata', {})
    preparation = metadata.get('recognition_preparation', {}) if isinstance(metadata, dict) else {}
    contract = preparation.get('contract', {}) if isinstance(preparation, dict) else {}
    contract = contract if isinstance(contract, dict) else {}
    scores = getattr(result, 'probabilities', {})
    data = RecognitionInput(top_class=getattr(result, 'top_class', None),
                            probabilities=scores if isinstance(scores, dict) else {}, probability=getattr(result, 'probability', None),
                            artifact_accepted=getattr(result, 'artifact_accepted', False),
                            artifact_threshold=getattr(result, 'artifact_threshold', None),
                            capture_status=_capture_status(result), model_available=getattr(result, 'model_available', True),
                            processing_compatible=getattr(result, 'processing_compatible', True),
                            outside_scope=getattr(result, 'outside_scope', False), model_type=getattr(result, 'model_type', ''),
                            model_sha256=getattr(result, 'model_sha256', ''), encoder_sha256=getattr(result, 'encoder_sha256', ''),
                            head_sha256=getattr(result, 'head_sha256', ''), processing_sha256=contract.get('sha256', ''))
    return decide_recognition(data, policy)


def decision_for_result(result: Any, config: AppConfig) -> RecognitionSafetyDecision:
    """Re-read current policy/evidence on every render so revocation invalidates cached UI results."""
    return build_recognition_safety_decision(result, policy=load_decision_policy(config))


def decision_from_error(exc: BaseException) -> RecognitionSafetyDecision:
    from ecoscan.image_processing.validation import ImageValidationError
    if isinstance(exc, ImageValidationError):
        return RecognitionSafetyDecision('retake', 'danger', 'Imagem inválida: refaça a foto',
                                         'O arquivo não pôde ser usado para reconhecimento.',
                                         'Envie uma foto válida ou escolha o material manualmente.',
                                         decision_reason=('invalid_image',))
    return RecognitionSafetyDecision('model_unavailable', 'warn', 'Reconhecimento indisponível',
                                     'Não foi possível concluir a análise.', 'Escolha o material manualmente ou tente novamente.',
                                     decision_reason=('model_unavailable',))


def record_decision(decision: RecognitionSafetyDecision) -> None:
    """Process-local private counters/events. No account, file path, photo, or free text."""
    with _LOCK:
        _COUNTS['total'] += 1
        _COUNTS[decision.status] += 1
    LOGGER.info('recognition_decision status=%s decision_reason=%s policy_version=%s policy_sha256=%s model_sha256=%s processing_sha256=%s evidence_sha256=%s engine_version=%s engine_sha256=%s',
                decision.status, ','.join(decision.decision_reason), decision.policy_version, decision.policy_sha256,
                decision.model_sha256, decision.processing_sha256, decision.evidence_sha256, decision.engine_version, decision.engine_sha256)


def decision_metrics_snapshot() -> dict[str, float | int]:
    with _LOCK:
        counts = dict(_COUNTS)
    total = counts.get('total', 0)
    rejected = sum(counts.get(s, 0) for s in ('unrecognized', 'out_of_scope', 'retake', 'model_unavailable'))
    return {**counts, 'rejected': rejected, 'rejection_rate': rejected / total if total else 0.0,
            'identified_rate': counts.get('identified', 0) / total if total else 0.0}


def capture_photo_tips() -> tuple[str, ...]:
    return ('fotografe um resíduo principal por vez;', 'use fundo simples e boa iluminação;',
            'deixe o objeto inteiro visível, incluindo topo, base ou tampa;',
            'evite reflexos fortes em vidro, metal e plástico transparente;',
            'se houver dúvida, tire outra foto em ângulo diferente.')
