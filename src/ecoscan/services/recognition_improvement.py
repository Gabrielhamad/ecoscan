from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

from ecoscan.services.diagnostics import DatasetStatus
from ecoscan.services.field_testing import FieldTestRecord
from ecoscan.services.history import HistoryEntry
from ecoscan.services.recognition_feedback import RecognitionFeedback


@dataclass(frozen=True)
class RecognitionPriority:
    class_id: str
    label: str
    priority: str
    score: float
    action: str
    analyses: int
    low_confidence: int
    corrections_as_expected: int
    false_positive_corrections: int
    field_wrong_count: int
    field_inconclusive_count: int
    raw_images: int
    curated_images: int
    average_confidence: float | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RecognitionConfusion:
    predicted_class: str
    expected_class: str
    predicted_label: str
    expected_label: str
    occurrences: int
    latest_confidence: float | None
    latest_note: str
    action: str


@dataclass(frozen=True)
class RecognitionImprovementPlan:
    priorities: tuple[RecognitionPriority, ...]
    confusions: tuple[RecognitionConfusion, ...]
    recommendations: tuple[str, ...]


def build_recognition_improvement_plan(
    history_entries: Iterable[HistoryEntry],
    feedback_entries: Iterable[RecognitionFeedback],
    dataset_status: DatasetStatus,
    class_labels: dict[str, str],
    *,
    field_test_entries: Iterable[FieldTestRecord] = (),
    classes: Iterable[str] = (),
    target_raw_per_class: int = 50,
    low_confidence_threshold: float = 0.72,
) -> RecognitionImprovementPlan:
    history = tuple(history_entries)
    feedback = tuple(feedback_entries)
    field_tests = tuple(field_test_entries)
    class_ids = _all_class_ids(classes, class_labels, dataset_status, history, feedback, field_tests)

    analysis_count: Counter[str] = Counter()
    low_confidence_count: Counter[str] = Counter()
    probabilities: dict[str, list[float]] = defaultdict(list)
    expected_corrections: Counter[str] = Counter()
    false_positive_corrections: Counter[str] = Counter()
    field_wrong_count: Counter[str] = Counter()
    field_inconclusive_count: Counter[str] = Counter()

    for entry in history:
        class_id = entry.top_class or entry.predicted_class or "__inconclusivo__"
        analysis_count[class_id] += 1
        if entry.probability is not None:
            probabilities[class_id].append(entry.probability)
            if entry.probability < low_confidence_threshold:
                low_confidence_count[class_id] += 1

    for item in feedback:
        predicted = item.predicted_class or item.top_class or "__inconclusivo__"
        expected = item.expected_class
        if expected and expected != predicted:
            expected_corrections[expected] += 1
            false_positive_corrections[predicted] += 1

    for item in field_tests:
        if not item.expected_class:
            continue
        if item.result_status == "errou":
            field_wrong_count[item.expected_class] += 1
            if item.model_class:
                false_positive_corrections[item.model_class] += 1
        elif item.result_status == "inconclusivo":
            field_inconclusive_count[item.expected_class] += 1

    priorities = tuple(
        sorted(
            (
                _build_priority(
                    class_id,
                    class_labels,
                    dataset_status,
                    analysis_count,
                    low_confidence_count,
                    probabilities,
                    expected_corrections,
                    false_positive_corrections,
                    field_wrong_count,
                    field_inconclusive_count,
                    target_raw_per_class=target_raw_per_class,
                    low_confidence_threshold=low_confidence_threshold,
                )
                for class_id in class_ids
            ),
            key=lambda item: (-item.score, item.label),
        )
    )
    confusions = _build_confusions(feedback, field_tests, class_labels)
    recommendations = _build_recommendations(priorities, confusions, history, feedback, field_tests)
    return RecognitionImprovementPlan(priorities, confusions, recommendations)


def priority_table_rows(priorities: Iterable[RecognitionPriority], *, limit: int = 8) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in tuple(priorities)[:limit]:
        rows.append(
            {
                "prioridade": item.priority,
                "classe": item.label,
                "score": round(item.score, 1),
                "ação": item.action,
                "análises": item.analyses,
                "baixa_confiança": item.low_confidence,
                "correções": item.corrections_as_expected + item.false_positive_corrections,
                "erros_campo": item.field_wrong_count,
                "inconclusivos_campo": item.field_inconclusive_count,
                "brutas": item.raw_images,
                "curadas": item.curated_images,
                "confiança_média": (
                    round(item.average_confidence, 3) if item.average_confidence is not None else None
                ),
                "motivos": "; ".join(item.reasons),
            }
        )
    return rows


def confusion_table_rows(confusions: Iterable[RecognitionConfusion], *, limit: int = 8) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in tuple(confusions)[:limit]:
        rows.append(
            {
                "modelo_indicou": item.predicted_label,
                "correto": item.expected_label,
                "ocorrências": item.occurrences,
                "última_confiança": item.latest_confidence,
                "ação": item.action,
                "observação": item.latest_note,
            }
        )
    return rows


def _all_class_ids(
    classes: Iterable[str],
    class_labels: dict[str, str],
    dataset_status: DatasetStatus,
    history: tuple[HistoryEntry, ...],
    feedback: tuple[RecognitionFeedback, ...],
    field_tests: tuple[FieldTestRecord, ...],
) -> tuple[str, ...]:
    values = set(classes) | set(class_labels)
    values.update(dataset_status.raw_counts)
    values.update(dataset_status.curated_counts)
    for entry in history:
        if entry.predicted_class:
            values.add(entry.predicted_class)
        if entry.top_class:
            values.add(entry.top_class)
    for item in feedback:
        if item.expected_class:
            values.add(item.expected_class)
        if item.predicted_class:
            values.add(item.predicted_class)
        if item.top_class:
            values.add(item.top_class)
    for item in field_tests:
        if item.expected_class:
            values.add(item.expected_class)
        if item.model_class:
            values.add(item.model_class)
    values.discard("")
    values.discard("__inconclusivo__")
    return tuple(sorted(values))


def _build_priority(
    class_id: str,
    class_labels: dict[str, str],
    dataset_status: DatasetStatus,
    analysis_count: Counter[str],
    low_confidence_count: Counter[str],
    probabilities: dict[str, list[float]],
    expected_corrections: Counter[str],
    false_positive_corrections: Counter[str],
    field_wrong_count: Counter[str],
    field_inconclusive_count: Counter[str],
    *,
    target_raw_per_class: int,
    low_confidence_threshold: float,
) -> RecognitionPriority:
    label = class_labels.get(class_id, class_id)
    raw_images = dataset_status.raw_counts.get(class_id, 0)
    curated_images = dataset_status.curated_counts.get(class_id, 0)
    dataset_gap = max(0, target_raw_per_class - raw_images)
    class_probabilities = probabilities.get(class_id, [])
    average_confidence = (
        sum(class_probabilities) / len(class_probabilities)
        if class_probabilities
        else None
    )
    average_penalty = (
        max(0.0, low_confidence_threshold - average_confidence) * 100
        if average_confidence is not None
        else (10 if raw_images < target_raw_per_class else 0)
    )
    score = min(
        100.0,
        dataset_gap * 0.45
        + low_confidence_count[class_id] * 7
        + expected_corrections[class_id] * 14
        + false_positive_corrections[class_id] * 10
        + field_wrong_count[class_id] * 16
        + field_inconclusive_count[class_id] * 9
        + average_penalty
        + (12 if analysis_count[class_id] == 0 and dataset_gap > 0 else 0)
        + (5 if raw_images > 0 and curated_images == 0 else 0),
    )
    priority = "alta" if score >= 60 else "média" if score >= 30 else "baixa"
    reasons = _priority_reasons(
        dataset_gap=dataset_gap,
        low_confidence=low_confidence_count[class_id],
        expected_corrections=expected_corrections[class_id],
        false_positive_corrections=false_positive_corrections[class_id],
        field_wrong=field_wrong_count[class_id],
        field_inconclusive=field_inconclusive_count[class_id],
        average_confidence=average_confidence,
    )
    return RecognitionPriority(
        class_id=class_id,
        label=label,
        priority=priority,
        score=round(score, 1),
        action=_priority_action(
            label,
            dataset_gap=dataset_gap,
            low_confidence=low_confidence_count[class_id],
            expected_corrections=expected_corrections[class_id],
            false_positive_corrections=false_positive_corrections[class_id],
            field_wrong=field_wrong_count[class_id],
            field_inconclusive=field_inconclusive_count[class_id],
        ),
        analyses=analysis_count[class_id],
        low_confidence=low_confidence_count[class_id],
        corrections_as_expected=expected_corrections[class_id],
        false_positive_corrections=false_positive_corrections[class_id],
        field_wrong_count=field_wrong_count[class_id],
        field_inconclusive_count=field_inconclusive_count[class_id],
        raw_images=raw_images,
        curated_images=curated_images,
        average_confidence=average_confidence,
        reasons=reasons,
    )


def _priority_reasons(
    *,
    dataset_gap: int,
    low_confidence: int,
    expected_corrections: int,
    false_positive_corrections: int,
    field_wrong: int,
    field_inconclusive: int,
    average_confidence: float | None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if dataset_gap > 0:
        reasons.append(f"faltam {dataset_gap} imagens brutas para a meta")
    if expected_corrections > 0:
        reasons.append(f"{expected_corrections} correção(ões) marcaram esta classe como correta")
    if false_positive_corrections > 0:
        reasons.append(f"{false_positive_corrections} vez(es) o modelo indicou esta classe indevidamente")
    if low_confidence > 0:
        reasons.append(f"{low_confidence} análise(s) com baixa confiança")
    if field_wrong > 0:
        reasons.append(f"{field_wrong} erro(s) registrado(s) em teste de campo")
    if field_inconclusive > 0:
        reasons.append(f"{field_inconclusive} teste(s) de campo inconclusivo(s)")
    if average_confidence is not None:
        reasons.append(f"confiança média {average_confidence:.0%}")
    return tuple(reasons or ("sem alerta crítico no lote atual",))


def _priority_action(
    label: str,
    *,
    dataset_gap: int,
    low_confidence: int,
    expected_corrections: int,
    false_positive_corrections: int,
    field_wrong: int,
    field_inconclusive: int,
) -> str:
    if field_wrong and expected_corrections:
        return f"Priorizar lote real de {label}, usando correções e testes de campo como casos de validação."
    if field_wrong:
        return f"Reforçar {label} com fotos reais dos cenários em que o grupo registrou erro."
    if field_inconclusive:
        return f"Testar novamente {label} com melhor iluminação e adicionar fotos variadas ao lote de treino."
    if expected_corrections and false_positive_corrections:
        return f"Montar lote comparativo de {label} com classes parecidas e revisar as correções antes do próximo treino."
    if expected_corrections:
        return f"Coletar mais fotos reais de {label}, priorizando os cenários que o usuário corrigiu."
    if false_positive_corrections:
        return f"Adicionar exemplos negativos parecidos para o modelo parar de confundir outros materiais com {label}."
    if dataset_gap > 0:
        return f"Coletar pelo menos {dataset_gap} fotos variadas de {label} para equilibrar a base."
    if low_confidence > 0:
        return f"Repetir testes de {label} com fundos, luz e ângulos diferentes para medir estabilidade."
    return f"Manter {label} em monitoramento e usar novas correções como evidência."


def _build_confusions(
    feedback: tuple[RecognitionFeedback, ...],
    field_tests: tuple[FieldTestRecord, ...],
    class_labels: dict[str, str],
) -> tuple[RecognitionConfusion, ...]:
    counter: Counter[tuple[str, str]] = Counter()
    latest_note: dict[tuple[str, str], str] = {}
    latest_confidence: dict[tuple[str, str], float | None] = {}
    for item in feedback:
        predicted = item.predicted_class or item.top_class or "__inconclusivo__"
        expected = item.expected_class
        if not expected or expected == predicted:
            continue
        key = (predicted, expected)
        counter[key] += 1
        latest_note[key] = item.note
        latest_confidence[key] = item.probability

    for item in field_tests:
        expected = item.expected_class
        if item.result_status == "acertou" or not expected:
            continue
        predicted = item.model_class or "__inconclusivo__"
        if predicted == expected:
            continue
        key = (predicted, expected)
        counter[key] += 1
        latest_note[key] = item.note
        latest_confidence[key] = item.confidence

    confusions: list[RecognitionConfusion] = []
    for (predicted, expected), occurrences in counter.most_common():
        predicted_label = class_labels.get(predicted, "Inconclusivo" if predicted == "__inconclusivo__" else predicted)
        expected_label = class_labels.get(expected, expected)
        confusions.append(
            RecognitionConfusion(
                predicted_class=predicted,
                expected_class=expected,
                predicted_label=predicted_label,
                expected_label=expected_label,
                occurrences=occurrences,
                latest_confidence=latest_confidence.get((predicted, expected)),
                latest_note=latest_note.get((predicted, expected), ""),
                action=(
                    f"Criar fotos comparativas: {expected_label} verdadeiro versus {predicted_label}, "
                    "com fundo real, variação de luz e ângulos próximos."
                ),
            )
        )
    return tuple(confusions)


def _build_recommendations(
    priorities: tuple[RecognitionPriority, ...],
    confusions: tuple[RecognitionConfusion, ...],
    history: tuple[HistoryEntry, ...],
    feedback: tuple[RecognitionFeedback, ...],
    field_tests: tuple[FieldTestRecord, ...],
) -> tuple[str, ...]:
    if not history and not feedback and not field_tests:
        return (
            "Iniciar rodada de testes com fotos reais do grupo e manter o histórico ativado.",
            "Toda classificação errada deve ser corrigida na interface para virar evidência de treino.",
            "Antes de retreinar, revisar imagens duplicadas, baixa qualidade e classes desbalanceadas.",
        )

    actions: list[str] = []
    high_priority = [item.label for item in priorities if item.priority == "alta"][:3]
    if high_priority:
        actions.append("Priorizar reforço de imagem para: " + ", ".join(high_priority) + ".")
    elif priorities:
        actions.append("Manter rodada de monitoramento e reforçar as classes com maior score de melhoria.")

    if confusions:
        top = confusions[0]
        actions.append(
            f"Tratar primeiro a confusão {top.predicted_label} → {top.expected_label}, "
            f"registrada {top.occurrences} vez(es)."
        )

    actions.append("Promover novo modelo somente com validação separada e comparação de métricas antes/depois.")
    return tuple(actions)
