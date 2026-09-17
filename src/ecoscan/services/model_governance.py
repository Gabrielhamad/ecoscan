from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ecoscan.config import AppConfig
from ecoscan.services.completion import build_completion_plan
from ecoscan.services.diagnostics import model_status
from ecoscan.services.field_testing import FieldTestRecord
from ecoscan.services.recognition_feedback import RecognitionFeedback


@dataclass(frozen=True)
class ModelMetricSnapshot:
    report_id: str
    model_kind: str
    split: str
    accuracy: float | None
    macro_precision: float | None
    macro_recall: float | None
    macro_f1: float | None
    total: int
    uncertain_count: int
    path: str


@dataclass(frozen=True)
class ModelGate:
    title: str
    status: str
    evidence: str
    detail: str
    next_step: str


@dataclass(frozen=True)
class HardCase:
    source: str
    timestamp_utc: str
    expected_class: str
    predicted_class: str | None
    status: str
    confidence: float | None
    note: str
    action: str


@dataclass(frozen=True)
class ModelGovernancePlan:
    promotion_status: str
    promotion_label: str
    active_model_kind: str
    final_model_path: str
    evaluation_count: int
    reference_metric: ModelMetricSnapshot | None
    candidate_metric: ModelMetricSnapshot | None
    gates: tuple[ModelGate, ...]
    hard_cases: tuple[HardCase, ...]
    recommendations: tuple[str, ...]


def build_model_governance_plan(
    config: AppConfig,
    *,
    feedback_entries: Iterable[RecognitionFeedback] = (),
    field_test_entries: Iterable[FieldTestRecord] = (),
    class_labels: dict[str, str] | None = None,
    min_macro_f1_gain: float = 0.03,
    min_hard_cases: int = 5,
) -> ModelGovernancePlan:
    labels = class_labels or {}
    selected_model = model_status(config)
    completion_plan = build_completion_plan(config)
    snapshots = read_evaluation_snapshots(config)
    hard_cases = build_hard_cases(feedback_entries, field_test_entries, labels)
    reference_metric = _select_reference_metric(snapshots)
    candidate_metric = _select_final_candidate_metric(snapshots)
    promotion_ok = _candidate_beats_reference(candidate_metric, reference_metric, min_macro_f1_gain)

    gates = _build_gates(
        completion_plan.ready_for_final_training,
        selected_model.final_model_exists,
        selected_model.final_model_path,
        snapshots,
        reference_metric,
        candidate_metric,
        hard_cases,
        promotion_ok,
        min_hard_cases=min_hard_cases,
        min_macro_f1_gain=min_macro_f1_gain,
    )
    promotion_status, promotion_label = _promotion_summary(
        final_model_exists=selected_model.final_model_exists,
        candidate_metric=candidate_metric,
        reference_metric=reference_metric,
        promotion_ok=promotion_ok,
    )
    return ModelGovernancePlan(
        promotion_status=promotion_status,
        promotion_label=promotion_label,
        active_model_kind=selected_model.selected_kind,
        final_model_path=selected_model.final_model_path,
        evaluation_count=len(snapshots),
        reference_metric=reference_metric,
        candidate_metric=candidate_metric,
        gates=tuple(gates),
        hard_cases=hard_cases,
        recommendations=_build_recommendations(
            selected_model.final_model_exists,
            completion_plan.ready_for_final_training,
            reference_metric,
            candidate_metric,
            hard_cases,
            min_macro_f1_gain=min_macro_f1_gain,
        ),
    )


def read_evaluation_snapshots(config: AppConfig) -> tuple[ModelMetricSnapshot, ...]:
    evaluation_dir = config.directories["reports"] / "evaluation"
    if not evaluation_dir.exists():
        return ()

    snapshots: list[ModelMetricSnapshot] = []
    for path in sorted(evaluation_dir.glob("*/metrics.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        snapshots.append(_snapshot_from_payload(path, payload))
    return tuple(snapshots)


def build_hard_cases(
    feedback_entries: Iterable[RecognitionFeedback],
    field_test_entries: Iterable[FieldTestRecord],
    class_labels: dict[str, str] | None = None,
) -> tuple[HardCase, ...]:
    labels = class_labels or {}
    cases: list[HardCase] = []

    for item in feedback_entries:
        predicted = item.predicted_class or item.top_class
        if not item.expected_class or predicted == item.expected_class:
            continue
        cases.append(
            HardCase(
                source="correção do usuário",
                timestamp_utc=item.timestamp_utc,
                expected_class=item.expected_class,
                predicted_class=predicted,
                status="errou",
                confidence=item.probability,
                note=item.note,
                action=_hard_case_action(item.expected_class, predicted, labels),
            )
        )

    for item in field_test_entries:
        if item.result_status == "acertou" and item.model_class == item.expected_class:
            continue
        if not item.expected_class:
            continue
        cases.append(
            HardCase(
                source="teste de campo",
                timestamp_utc=item.timestamp_utc,
                expected_class=item.expected_class,
                predicted_class=item.model_class,
                status=item.result_status,
                confidence=item.confidence,
                note=item.note,
                action=_hard_case_action(item.expected_class, item.model_class, labels),
            )
        )

    return tuple(sorted(cases, key=lambda item: item.timestamp_utc, reverse=True))


def model_gate_table_rows(gates: Iterable[ModelGate]) -> list[dict[str, str]]:
    return [
        {
            "critério": gate.title,
            "status": gate.status,
            "evidência": gate.evidence,
            "detalhe": gate.detail,
            "próximo_passo": gate.next_step,
        }
        for gate in gates
    ]


def metric_snapshot_rows(plan: ModelGovernancePlan) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for role, metric in (("referência atual", plan.reference_metric), ("candidato final", plan.candidate_metric)):
        if metric is None:
            continue
        rows.append(
            {
                "papel": role,
                "relatório": metric.report_id,
                "modelo": metric.model_kind,
                "split": metric.split,
                "accuracy": _round_metric(metric.accuracy),
                "macro_f1": _round_metric(metric.macro_f1),
                "macro_recall": _round_metric(metric.macro_recall),
                "total": metric.total,
                "inconclusivos": metric.uncertain_count,
                "arquivo": metric.path,
            }
        )
    return rows


def hard_case_table_rows(
    hard_cases: Iterable[HardCase],
    class_labels: dict[str, str],
    *,
    limit: int = 20,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in tuple(hard_cases)[:limit]:
        rows.append(
            {
                "origem": item.source,
                "data_utc": item.timestamp_utc,
                "esperado": class_labels.get(item.expected_class, item.expected_class),
                "modelo": class_labels.get(item.predicted_class or "", item.predicted_class or "não reconheceu"),
                "status": item.status,
                "confiança": _round_metric(item.confidence),
                "ação": item.action,
                "observação": item.note,
            }
        )
    return rows


def _snapshot_from_payload(path: Path, payload: dict[str, Any]) -> ModelMetricSnapshot:
    return ModelMetricSnapshot(
        report_id=path.parent.name,
        model_kind=str(payload.get("model_kind", path.parent.name)),
        split=str(payload.get("split", "")),
        accuracy=_optional_float(payload.get("accuracy")),
        macro_precision=_optional_float(payload.get("macro_precision")),
        macro_recall=_optional_float(payload.get("macro_recall")),
        macro_f1=_optional_float(payload.get("macro_f1")),
        total=int(payload.get("total", 0) or 0),
        uncertain_count=int(payload.get("uncertain_count", 0) or 0),
        path=str(path),
    )


def _select_reference_metric(snapshots: tuple[ModelMetricSnapshot, ...]) -> ModelMetricSnapshot | None:
    non_candidates = [item for item in snapshots if not _is_final_candidate(item)]
    candidates = non_candidates or list(snapshots)
    return max(candidates, key=_metric_sort_key, default=None)


def _select_final_candidate_metric(snapshots: tuple[ModelMetricSnapshot, ...]) -> ModelMetricSnapshot | None:
    candidates = [item for item in snapshots if _is_final_candidate(item)]
    return max(candidates, key=_metric_sort_key, default=None)


def _metric_sort_key(snapshot: ModelMetricSnapshot) -> tuple[float, float, int]:
    return (
        snapshot.macro_f1 if snapshot.macro_f1 is not None else -1.0,
        snapshot.accuracy if snapshot.accuracy is not None else -1.0,
        snapshot.total,
    )


def _is_final_candidate(snapshot: ModelMetricSnapshot) -> bool:
    text = f"{snapshot.report_id} {snapshot.model_kind}".lower()
    return "transfer" in text or "final" in text or "candidate_final" in text


def _candidate_beats_reference(
    candidate: ModelMetricSnapshot | None,
    reference: ModelMetricSnapshot | None,
    min_macro_f1_gain: float,
) -> bool:
    if candidate is None or reference is None:
        return False
    if candidate.macro_f1 is None or reference.macro_f1 is None:
        return False
    return candidate.macro_f1 >= reference.macro_f1 + min_macro_f1_gain


def _build_gates(
    ready_for_final_training: bool,
    final_model_exists: bool,
    final_model_path: str,
    snapshots: tuple[ModelMetricSnapshot, ...],
    reference_metric: ModelMetricSnapshot | None,
    candidate_metric: ModelMetricSnapshot | None,
    hard_cases: tuple[HardCase, ...],
    promotion_ok: bool,
    *,
    min_hard_cases: int,
    min_macro_f1_gain: float,
) -> list[ModelGate]:
    return [
        ModelGate(
            title="Dataset curado para treino final",
            status="ok" if ready_for_final_training else "attention",
            evidence="data/curated; reports/dataset_readiness",
            detail=(
                "Base curada alcança o alvo mínimo para treino final."
                if ready_for_final_training
                else "A curadoria ainda precisa de mais imagens reais, revisadas e balanceadas por classe."
            ),
            next_step="Completar data/curated antes do treino final por transfer learning.",
        ),
        ModelGate(
            title="Modelo final treinado",
            status="ok" if final_model_exists else "pending",
            evidence=final_model_path,
            detail=(
                "Arquivo do modelo final encontrado."
                if final_model_exists
                else "O sistema continua usando o modelo visual atual enquanto o modelo final não existe."
            ),
            next_step="Treinar o modelo final somente após fechar a curadoria do dataset.",
        ),
        ModelGate(
            title="Avaliação comparativa registrada",
            status="ok" if reference_metric and candidate_metric else ("attention" if snapshots else "pending"),
            evidence="reports/evaluation/*/metrics.json",
            detail=(
                "Há métricas de referência e candidato final para comparação."
                if reference_metric and candidate_metric
                else f"{len(snapshots)} relatório(s) encontrado(s), mas ainda falta avaliação do candidato final."
            ),
            next_step="Gerar relatório de teste do modelo final e comparar contra a melhor referência atual.",
        ),
        ModelGate(
            title="Casos difíceis de regressão",
            status="ok" if len(hard_cases) >= min_hard_cases else ("attention" if hard_cases else "pending"),
            evidence="reports/recognition_feedback; reports/field_tests",
            detail=f"{len(hard_cases)} caso(s) difícil(eis) registrado(s) para revalidar o modelo.",
            next_step="Manter erros reais como lote fixo de regressão: lata, garrafa, eletrônico, pilha e itens perigosos.",
        ),
        ModelGate(
            title="Regra de promoção segura",
            status="ok" if promotion_ok else "pending",
            evidence="macro_f1, accuracy e confusões críticas",
            detail=(
                f"Candidato supera a referência em pelo menos {min_macro_f1_gain:.0%} de macro-F1."
                if promotion_ok
                else f"O modelo final só deve ser promovido se superar a referência em pelo menos {min_macro_f1_gain:.0%} de macro-F1."
            ),
            next_step="Não substituir o modelo ativo sem ganho medido e sem passar nos casos difíceis.",
        ),
    ]


def _promotion_summary(
    *,
    final_model_exists: bool,
    candidate_metric: ModelMetricSnapshot | None,
    reference_metric: ModelMetricSnapshot | None,
    promotion_ok: bool,
) -> tuple[str, str]:
    if not final_model_exists:
        return "prepared", "Governança pronta; aguardando dataset curado e treino final."
    if candidate_metric is None:
        return "attention", "Modelo final existe, mas ainda falta avaliação comparativa."
    if reference_metric is None:
        return "attention", "Falta métrica de referência para decidir promoção."
    if promotion_ok:
        return "ready", "Modelo final pode ser candidato a promoção, após revisão dos casos difíceis."
    return "blocked", "Modelo final ainda não deve ser promovido: não superou a referência mínima."


def _build_recommendations(
    final_model_exists: bool,
    ready_for_final_training: bool,
    reference_metric: ModelMetricSnapshot | None,
    candidate_metric: ModelMetricSnapshot | None,
    hard_cases: tuple[HardCase, ...],
    *,
    min_macro_f1_gain: float,
) -> tuple[str, ...]:
    actions: list[str] = []
    if not ready_for_final_training:
        actions.append("Finalizar curadoria por classe antes de treinar o modelo definitivo.")
    if not final_model_exists:
        actions.append("Manter o reconhecimento atual como orientativo e registrar erros reais durante os testes.")
    if reference_metric is not None:
        actions.append(
            f"Usar {reference_metric.report_id} como referência inicial: macro-F1 {_format_metric(reference_metric.macro_f1)}."
        )
    if candidate_metric is None:
        actions.append(
            "Quando houver novo treino, gerar metrics.json no teste separado antes de alterar o modelo ativo."
        )
    else:
        actions.append(
            f"Exigir ganho mínimo de {min_macro_f1_gain:.0%} de macro-F1 contra a referência antes da promoção."
        )
    if hard_cases:
        actions.append(
            f"Reexecutar os {len(hard_cases)} caso(s) difícil(eis) registrados e bloquear promoção se erro crítico voltar."
        )
    else:
        actions.append("Registrar erros de campo e correções do usuário para formar o lote de regressão obrigatório.")
    return tuple(actions)


def _hard_case_action(expected: str, predicted: str | None, class_labels: dict[str, str]) -> str:
    expected_label = class_labels.get(expected, expected)
    predicted_label = class_labels.get(predicted or "", predicted or "não reconhecido")
    if predicted:
        return f"Revalidar {expected_label} contra {predicted_label} antes de promover novo modelo."
    return f"Revalidar {expected_label} em iluminação, fundo e ângulo variados antes de promover novo modelo."


def _optional_float(value: object) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _round_metric(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def _format_metric(value: float | None) -> str:
    return "indisponível" if value is None else f"{value:.1%}"
