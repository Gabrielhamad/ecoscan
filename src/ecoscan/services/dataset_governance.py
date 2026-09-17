from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ecoscan.config import AppConfig
from ecoscan.disposal.guidance import DisposalGuidance, load_guidance
from ecoscan.services.diagnostics import dataset_status


@dataclass(frozen=True)
class ClassReadiness:
    class_id: str
    display_name: str
    environmental_category: str
    raw_count: int
    curated_count: int
    train_count: int
    validation_count: int
    test_count: int
    target_per_class: int
    missing_raw: int
    missing_curated: int
    is_special_waste: bool
    gate: str
    next_action: str


@dataclass(frozen=True)
class DatasetReadinessSummary:
    target_per_class: int
    class_count: int
    raw_total: int
    curated_total: int
    split_total: int
    classes_at_raw_target: int
    classes_at_curated_target: int
    missing_raw_total: int
    missing_curated_total: int
    special_waste_raw_total: int
    ready_for_final_training: bool


def _load_guidance(config: AppConfig) -> dict[str, DisposalGuidance]:
    path = config.project_root / "config" / "disposal_guidance.json"
    try:
        return load_guidance(path)
    except Exception:
        return {}


def _is_special(category: str) -> bool:
    normalized = category.lower()
    return any(token in normalized for token in ("especial", "eletro", "perigoso", "químico", "quimico"))


def _gate_and_action(raw_count: int, curated_count: int, target: int) -> tuple[str, str]:
    if curated_count >= target:
        return "ready", "Classe pronta para split/treinamento final."
    if raw_count >= target and curated_count == 0:
        return "needs_curation", "Revisar imagens e aplicar curadoria antes do treino final."
    if raw_count >= target:
        return "needs_curated_volume", "Completar curadoria até atingir o volume mínimo por classe."
    missing = target - raw_count
    return "needs_images", f"Coletar pelo menos mais {missing} imagem(ns) úteis."


def build_class_readiness(config: AppConfig, *, target_per_class: int = 50) -> list[ClassReadiness]:
    status = dataset_status(config)
    guidance = _load_guidance(config)
    rows: list[ClassReadiness] = []

    for class_id in config.classes:
        raw_count = status.raw_counts[class_id]
        curated_count = status.curated_counts[class_id]
        guide = guidance.get(class_id)
        display_name = guide.display_name if guide else class_id
        category = guide.environmental_category if guide else "classe sem orientação"
        gate, next_action = _gate_and_action(raw_count, curated_count, target_per_class)
        rows.append(
            ClassReadiness(
                class_id=class_id,
                display_name=display_name,
                environmental_category=category,
                raw_count=raw_count,
                curated_count=curated_count,
                train_count=status.train_counts[class_id],
                validation_count=status.validation_counts[class_id],
                test_count=status.test_counts[class_id],
                target_per_class=target_per_class,
                missing_raw=max(0, target_per_class - raw_count),
                missing_curated=max(0, target_per_class - curated_count),
                is_special_waste=_is_special(category),
                gate=gate,
                next_action=next_action,
            )
        )
    return rows


def summarize_class_readiness(rows: list[ClassReadiness], *, target_per_class: int) -> DatasetReadinessSummary:
    raw_total = sum(row.raw_count for row in rows)
    curated_total = sum(row.curated_count for row in rows)
    split_total = sum(row.train_count + row.validation_count + row.test_count for row in rows)
    classes_at_raw_target = sum(1 for row in rows if row.raw_count >= target_per_class)
    classes_at_curated_target = sum(1 for row in rows if row.curated_count >= target_per_class)
    return DatasetReadinessSummary(
        target_per_class=target_per_class,
        class_count=len(rows),
        raw_total=raw_total,
        curated_total=curated_total,
        split_total=split_total,
        classes_at_raw_target=classes_at_raw_target,
        classes_at_curated_target=classes_at_curated_target,
        missing_raw_total=sum(row.missing_raw for row in rows),
        missing_curated_total=sum(row.missing_curated for row in rows),
        special_waste_raw_total=sum(row.raw_count for row in rows if row.is_special_waste),
        ready_for_final_training=bool(rows) and all(row.gate == "ready" for row in rows),
    )


def build_dataset_readiness(config: AppConfig, *, target_per_class: int = 50) -> tuple[
    DatasetReadinessSummary,
    list[ClassReadiness],
]:
    rows = build_class_readiness(config, target_per_class=target_per_class)
    return summarize_class_readiness(rows, target_per_class=target_per_class), rows


def _write_csv(path: Path, rows: list[ClassReadiness]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(rows[0]).keys()) if rows else [field.name for field in ClassReadiness.__dataclass_fields__.values()]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _format_markdown(summary: DatasetReadinessSummary, rows: list[ClassReadiness]) -> str:
    ready_text = "sim" if summary.ready_for_final_training else "não"
    lines = [
        "# Prontidão do dataset EcoScan",
        "",
        f"Alvo por classe: {summary.target_per_class} imagens curadas.",
        f"Pronto para treinamento final: {ready_text}.",
        "",
        "| Classe | Categoria | Raw | Curated | Faltam raw | Faltam curated | Gate | Próxima ação |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row.class_id} | {row.environmental_category} | {row.raw_count} | {row.curated_count} | "
            f"{row.missing_raw} | {row.missing_curated} | {row.gate} | {row.next_action} |"
        )
    lines.extend(
        [
            "",
            "## Resumo",
            "",
            f"- Total bruto: {summary.raw_total}",
            f"- Total curado: {summary.curated_total}",
            f"- Classes no alvo bruto: {summary.classes_at_raw_target}/{summary.class_count}",
            f"- Classes no alvo curado: {summary.classes_at_curated_target}/{summary.class_count}",
            f"- Imagens brutas ainda necessárias: {summary.missing_raw_total}",
            f"- Imagens curadas ainda necessárias: {summary.missing_curated_total}",
            f"- Imagens brutas de resíduos especiais: {summary.special_waste_raw_total}",
            "",
        ]
    )
    return "\n".join(lines)


def write_dataset_readiness_report(
    config: AppConfig,
    *,
    target_per_class: int = 50,
    output_dir: str | Path | None = None,
) -> dict[str, Path]:
    summary, rows = build_dataset_readiness(config, target_per_class=target_per_class)
    report_dir = Path(output_dir).resolve() if output_dir else config.directories["reports"] / "dataset_readiness"
    report_dir.mkdir(parents=True, exist_ok=True)

    csv_path = report_dir / "class_readiness.csv"
    json_path = report_dir / "dataset_readiness.json"
    markdown_path = report_dir / "dataset_readiness.md"

    _write_csv(csv_path, rows)
    json_path.write_text(
        json.dumps(
            {
                "summary": asdict(summary),
                "classes": [asdict(row) for row in rows],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    markdown_path.write_text(_format_markdown(summary, rows), encoding="utf-8")
    return {"csv": csv_path, "json": json_path, "markdown": markdown_path}
