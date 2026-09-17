from __future__ import annotations

import csv
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ecoscan.app.pipeline import ProcessingPipelineOptions, run_processing_pipeline
from ecoscan.config import AppConfig
from ecoscan.image_processing.image_io import save_image


@dataclass(frozen=True)
class PreparedImageRecord:
    class_id: str
    source_path: str
    target_path: str
    status: str
    reason: str
    capture_quality_status: str
    capture_quality_score: int
    filter_name: str
    filter_sequence: str
    segmentation_name: str
    foreground_ratio: float
    significant_elements: int
    largest_area_ratio: float
    likely_multi_object: bool
    brightness_before: float
    contrast_before: float
    sharpness_before: float


@dataclass(frozen=True)
class DatasetPreparationSummary:
    source_dir: str
    output_dir: str
    total_seen: int
    prepared: int
    rejected: int
    errors: int
    min_quality_score: int
    counts_by_class: dict[str, int]
    rejected_by_class: dict[str, int]


def _resolve_path(path: Path, project_root: Path) -> Path:
    resolved = path if path.is_absolute() else project_root / path
    return resolved.resolve()


def _safe_clear(path: Path, project_root: Path) -> None:
    resolved = _resolve_path(path, project_root)
    project = project_root.resolve()
    if resolved in {project, project.parent} or resolved.parent == resolved or len(resolved.parts) <= 2:
        raise ValueError(f"Refusing to clear unsafe directory: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    for child in resolved.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _iter_raw_images(source_dir: Path, classes: tuple[str, ...], extensions: frozenset[str]):
    for class_id in classes:
        class_dir = source_dir / class_id
        if not class_dir.exists():
            continue
        for path in sorted(class_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in extensions:
                yield class_id, path


def _relative(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


def _filter_sequence(metadata: dict[str, Any]) -> str:
    decision = dict(metadata.get("filter", {}).get("decision", {}))
    sequence = decision.get("selected_sequence") or [metadata.get("filter", {}).get("name", "unknown")]
    if not isinstance(sequence, list):
        return str(sequence)
    return " > ".join(str(item) for item in sequence)


def _acceptance_reason(metadata: dict[str, Any], min_quality_score: int) -> tuple[str, str]:
    capture_quality = dict(metadata.get("capture_quality", {}))
    elements = dict(metadata.get("elements", {}))
    score = int(capture_quality.get("score") or 0)
    quality_status = str(capture_quality.get("status") or "")
    significant = int(elements.get("significant_count") or 0)
    largest_area = float(elements.get("largest_area_ratio") or 0.0)

    if quality_status == "retake":
        return "rejected", "qualidade marcada como nova captura recomendada"
    if score < min_quality_score:
        return "rejected", f"pontuação de qualidade abaixo do mínimo ({score} < {min_quality_score})"
    if significant == 0:
        return "rejected", "nenhum elemento visual significativo após segmentação"
    if largest_area < 0.015:
        return "rejected", "elemento principal pequeno demais após segmentação"
    return "prepared", "imagem tratada e aprovada pela triagem automática"


def _record_from_result(
    *,
    class_id: str,
    source: Path,
    target: Path,
    status: str,
    reason: str,
    metadata: dict[str, Any],
    project_root: Path,
) -> PreparedImageRecord:
    capture_quality = dict(metadata.get("capture_quality", {}))
    filter_metadata = dict(metadata.get("filter", {}))
    segmentation_metadata = dict(metadata.get("segmentation", {}))
    elements = dict(metadata.get("elements", {}))
    quality = dict(metadata.get("quality", {}).get("before_filter", {}))

    return PreparedImageRecord(
        class_id=class_id,
        source_path=_relative(source, project_root),
        target_path=_relative(target, project_root) if status == "prepared" else "",
        status=status,
        reason=reason,
        capture_quality_status=str(capture_quality.get("status") or ""),
        capture_quality_score=int(capture_quality.get("score") or 0),
        filter_name=str(filter_metadata.get("name") or ""),
        filter_sequence=_filter_sequence(metadata),
        segmentation_name=str(segmentation_metadata.get("name") or ""),
        foreground_ratio=float(segmentation_metadata.get("foreground_ratio") or 0.0),
        significant_elements=int(elements.get("significant_count") or 0),
        largest_area_ratio=float(elements.get("largest_area_ratio") or 0.0),
        likely_multi_object=bool(elements.get("likely_multi_object")),
        brightness_before=float(quality.get("brightness_mean") or 0.0),
        contrast_before=float(quality.get("contrast") or 0.0),
        sharpness_before=float(quality.get("sharpness") or 0.0),
    )


def _error_record(
    *,
    class_id: str,
    source: Path,
    reason: str,
    project_root: Path,
) -> PreparedImageRecord:
    return PreparedImageRecord(
        class_id=class_id,
        source_path=_relative(source, project_root),
        target_path="",
        status="error",
        reason=reason,
        capture_quality_status="",
        capture_quality_score=0,
        filter_name="",
        filter_sequence="",
        segmentation_name="",
        foreground_ratio=0.0,
        significant_elements=0,
        largest_area_ratio=0.0,
        likely_multi_object=False,
        brightness_before=0.0,
        contrast_before=0.0,
        sharpness_before=0.0,
    )


def prepare_dataset_images(
    config: AppConfig,
    *,
    source_dir: Path | None = None,
    output_dir: Path | None = None,
    report_dir: Path | None = None,
    overwrite: bool = False,
    min_quality_score: int = 55,
) -> tuple[DatasetPreparationSummary, list[PreparedImageRecord]]:
    source_root = _resolve_path(source_dir or config.directories["raw_data"], config.project_root)
    output_root = _resolve_path(output_dir or config.directories["processed_data"], config.project_root)
    selected_report_dir = _resolve_path(
        report_dir or config.directories["reports"] / "dataset_preparation",
        config.project_root,
    )

    if overwrite:
        _safe_clear(output_root, config.project_root)
    output_root.mkdir(parents=True, exist_ok=True)
    selected_report_dir.mkdir(parents=True, exist_ok=True)

    records: list[PreparedImageRecord] = []
    counts_by_class = {class_id: 0 for class_id in config.classes}
    rejected_by_class = {class_id: 0 for class_id in config.classes}

    options = ProcessingPipelineOptions(filter_name="auto", segmentation_name="auto")
    for class_id, source in _iter_raw_images(source_root, config.classes, config.allowed_extensions):
        try:
            result = run_processing_pipeline(source, config, options)
            target = output_root / class_id / f"{source.stem}_processed.png"
            status, reason = _acceptance_reason(result.metadata, min_quality_score)
            if status == "prepared":
                save_image(result.model_input_preview, target)
                counts_by_class[class_id] += 1
            else:
                rejected_by_class[class_id] += 1
            records.append(
                _record_from_result(
                    class_id=class_id,
                    source=source,
                    target=target,
                    status=status,
                    reason=reason,
                    metadata=result.metadata,
                    project_root=config.project_root,
                )
            )
        except Exception as exc:
            rejected_by_class[class_id] += 1
            records.append(
                _error_record(
                    class_id=class_id,
                    source=source,
                    reason=str(exc),
                    project_root=config.project_root,
                )
            )

    summary = DatasetPreparationSummary(
        source_dir=_relative(source_root, config.project_root),
        output_dir=_relative(output_root, config.project_root),
        total_seen=len(records),
        prepared=sum(1 for record in records if record.status == "prepared"),
        rejected=sum(1 for record in records if record.status == "rejected"),
        errors=sum(1 for record in records if record.status == "error"),
        min_quality_score=int(min_quality_score),
        counts_by_class=counts_by_class,
        rejected_by_class=rejected_by_class,
    )
    _write_reports(summary, records, selected_report_dir)
    return summary, records


def _write_reports(
    summary: DatasetPreparationSummary,
    records: list[PreparedImageRecord],
    report_dir: Path,
) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "preparation_manifest.json"
    csv_path = report_dir / "preparation_manifest.csv"
    summary_path = report_dir / "preparation_summary.md"

    json_path.write_text(
        json.dumps(
            {
                "summary": asdict(summary),
                "images": [asdict(record) for record in records],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    fieldnames = list(PreparedImageRecord.__dataclass_fields__)
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))

    lines = [
        "# Preparação automática de imagens",
        "",
        f"Origem: `{summary.source_dir}`.",
        f"Saída: `{summary.output_dir}`.",
        f"Pontuação mínima de qualidade: {summary.min_quality_score}.",
        "",
        "## Resumo",
        "",
        f"- Imagens analisadas: {summary.total_seen}",
        f"- Imagens tratadas: {summary.prepared}",
        f"- Imagens rejeitadas: {summary.rejected}",
        f"- Erros: {summary.errors}",
        "",
        "## Imagens tratadas por classe",
        "",
        "| Classe | Tratadas | Rejeitadas/erro |",
        "|---|---:|---:|",
    ]
    for class_id in sorted(summary.counts_by_class):
        rejected = summary.rejected_by_class.get(class_id, 0)
        lines.append(f"| `{class_id}` | {summary.counts_by_class[class_id]} | {rejected} |")
    lines.extend(
        [
            "",
            "## Critério técnico",
            "",
            "Cada imagem aceita passou pelo pipeline de redimensionamento, filtragem adaptativa, segmentação adaptativa, análise de elementos e avaliação de qualidade de captura. A imagem salva em `data/processed` é a versão 224x224 já preparada para extração de características.",
            "",
            "Essa etapa não substitui curadoria humana; ela remove casos tecnicamente fracos e registra filtro/segmentação usados para auditoria.",
            "",
        ]
    )
    summary_path.write_text("\n".join(lines), encoding="utf-8")
