from __future__ import annotations

import csv
import json
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ecoscan.app.pipeline import ProcessingPipelineOptions
from ecoscan.config import AppConfig
from ecoscan.disposal.collection_points import filter_collection_points, load_collection_points
from ecoscan.disposal.guidance import load_guidance
from ecoscan.disposal.impact import load_environmental_impacts, missing_impacts_for_classes
from ecoscan.disposal.targets import load_disposal_targets, missing_targets_for_classes
from ecoscan.errors import error_catalog, public_error_payload
from ecoscan.image_processing.validation import ImageValidationError, validate_image_file
from ecoscan.live_camera.analyzer import LiveCameraAnalyzer
from ecoscan.services.accounts import load_user_profiles, profiles_path_from_config
from ecoscan.services.analysis_service import analyze_waste_image, load_model_bundle_for_analysis
from ecoscan.services.campaigns import load_campaign
from ecoscan.services.dataset_governance import build_dataset_readiness
from ecoscan.services.diagnostics import model_status
from ecoscan.services.photo_requirements import load_photo_requirements, missing_requirements_for_classes
from ecoscan.services.visual_report import save_pipeline_artifacts


@dataclass(frozen=True)
class AcceptanceCheckResult:
    code: str
    area: str
    status: str
    evidence: str
    details: str


@dataclass(frozen=True)
class AcceptanceCheckReport:
    generated_at_utc: str
    summary: dict[str, int]
    checks: tuple[AcceptanceCheckResult, ...]


def run_acceptance_checks(
    config: AppConfig,
    *,
    output_dir: str | Path | None = None,
    sample_image: str | Path | None = None,
) -> AcceptanceCheckReport:
    report_dir = Path(output_dir).resolve() if output_dir else config.directories["reports"] / "acceptance_checks"
    report_dir.mkdir(parents=True, exist_ok=True)

    checks: list[AcceptanceCheckResult] = []
    selected_sample = Path(sample_image).resolve() if sample_image else _find_sample_image(config)
    checks.append(_check_static_structure(config))
    checks.append(_check_guidance(config))
    checks.append(_check_disposal_targets(config))
    checks.append(_check_environmental_impacts(config))
    checks.append(_check_photo_requirements(config))
    checks.append(_check_collection_points(config))
    checks.append(_check_invalid_image_rejection(config))
    checks.extend(_check_model_and_pipeline(config, report_dir, selected_sample))
    checks.append(_check_dataset_readiness(config))
    checks.append(_check_final_model(config))
    checks.append(_check_error_contract())
    checks.append(_check_campaign_and_reports(config))
    checks.append(_check_accounts_and_admin(config))
    checks.append(_check_device_interface(config))

    report = AcceptanceCheckReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        summary=_summarize(checks),
        checks=tuple(checks),
    )
    _write_report(report, report_dir)
    return report


def _check_static_structure(config: AppConfig) -> AcceptanceCheckResult:
    required = [
        "src/ecoscan/ui/streamlit_app.py",
        "src/ecoscan/app/pipeline.py",
        "src/ecoscan/image_processing/filters.py",
        "src/ecoscan/segmentation/adaptive.py",
        "src/ecoscan/segmentation/methods.py",
        "src/ecoscan/classification/inference.py",
        "src/ecoscan/live_camera/server.py",
        "src/ecoscan/disposal/collection_points.py",
        "src/ecoscan/disposal/impact.py",
        "src/ecoscan/services/photo_requirements.py",
        "src/ecoscan/services/accounts.py",
        "src/ecoscan/services/campaigns.py",
        "src/ecoscan/services/civic_reports.py",
        "src/ecoscan/services/operations.py",
        "src/ecoscan/services/final_readiness.py",
        "src/ecoscan/services/recognition_safety.py",
        "src/ecoscan/services/usage_quality.py",
        "src/ecoscan/services/public_flow.py",
        "src/ecoscan/services/recognition_improvement.py",
        "src/ecoscan/services/model_governance.py",
        "src/ecoscan/services/deployment_readiness.py",
        "src/ecoscan/services/access_plan.py",
        "src/ecoscan/services/field_testing.py",
        "streamlit_app.py",
        "scripts/generate_final_readiness.py",
        "scripts/check_deployment_ready.py",
        "docs/hospedagem_gratuita.md",
        "docs/roteiro_etapas_profissionalizacao.md",
        "config/user_profiles.json",
        "config/campaigns.json",
        "tests",
    ]
    missing = [path for path in required if not (config.project_root / path).exists()]
    return AcceptanceCheckResult(
        "QA-01",
        "Estrutura",
        "ok" if not missing else "failed",
        ", ".join(required),
        "Estrutura principal encontrada." if not missing else "Itens ausentes: " + ", ".join(missing),
    )


def _check_guidance(config: AppConfig) -> AcceptanceCheckResult:
    guidance = load_guidance(config.project_root / "config" / "disposal_guidance.json")
    missing = [class_id for class_id in config.classes if class_id not in guidance]
    return AcceptanceCheckResult(
        "QA-02",
        "Orientações",
        "ok" if not missing else "attention",
        "config/disposal_guidance.json",
        "Todas as classes têm orientação." if not missing else "Sem orientação: " + ", ".join(missing),
    )


def _check_disposal_targets(config: AppConfig) -> AcceptanceCheckResult:
    try:
        targets = load_disposal_targets(config.project_root / "config" / "disposal_targets.json")
    except Exception as exc:
        return AcceptanceCheckResult(
            "QA-12",
            "Destinos",
            "failed",
            "config/disposal_targets.json",
            f"Falha ao carregar destinos de descarte: {exc}",
        )

    missing = missing_targets_for_classes(config.classes, targets)
    missing_assets = [
        target.asset_path
        for target in targets.values()
        if target.class_id in config.classes and not target.asset_absolute_path(config.project_root).exists()
    ]
    status = "ok" if not missing and not missing_assets else "attention"
    if missing:
        details = "Classes sem destino visual: " + ", ".join(missing)
    elif missing_assets:
        details = "Imagens de referência ausentes: " + ", ".join(missing_assets)
    else:
        details = "Classes ativas possuem cor, imagem de referência, preparo e busca no mapa."
    return AcceptanceCheckResult(
        "QA-12",
        "Destinos",
        status,
        "config/disposal_targets.json; assets/disposal_targets",
        details,
    )


def _check_environmental_impacts(config: AppConfig) -> AcceptanceCheckResult:
    try:
        impacts = load_environmental_impacts(config.project_root / "config" / "environmental_impacts.json")
    except Exception as exc:
        return AcceptanceCheckResult(
            "QA-13",
            "Impacto ambiental",
            "failed",
            "config/environmental_impacts.json",
            f"Falha ao carregar impactos ambientais: {exc}",
        )

    missing = missing_impacts_for_classes(config.classes, impacts)
    weak = [
        class_id
        for class_id in config.classes
        if class_id in impacts and len(impacts[class_id].bad_disposal_risks) < 2
    ]
    status = "ok" if not missing and not weak else "attention"
    if missing:
        details = "Classes sem impacto ambiental: " + ", ".join(missing)
    elif weak:
        details = "Classes com impacto ambiental pouco detalhado: " + ", ".join(weak)
    else:
        details = "Classes ativas possuem riscos do mau descarte, ação positiva e fonte de referência."
    return AcceptanceCheckResult(
        "QA-13",
        "Impacto ambiental",
        status,
        "config/environmental_impacts.json",
        details,
    )


def _check_photo_requirements(config: AppConfig) -> AcceptanceCheckResult:
    try:
        requirements = load_photo_requirements(config.project_root / "config" / "photo_requirements.json")
    except Exception as exc:
        return AcceptanceCheckResult(
            "QA-14",
            "Plano de fotos",
            "failed",
            "config/photo_requirements.json",
            f"Falha ao carregar plano de fotos: {exc}",
        )

    missing = missing_requirements_for_classes(config.classes, requirements)
    weak = [
        class_id
        for class_id in config.classes
        if class_id in requirements and len(requirements[class_id].examples) < 5
    ]
    status = "ok" if not missing and not weak else "attention"
    if missing:
        details = "Classes sem plano de fotos: " + ", ".join(missing)
    elif weak:
        details = "Classes com poucos exemplos de coleta: " + ", ".join(weak)
    else:
        details = "Classes ativas possuem exemplos, variações, restrições e meta mínima de imagens."
    return AcceptanceCheckResult(
        "QA-14",
        "Plano de fotos",
        status,
        "config/photo_requirements.json",
        details,
    )


def _check_collection_points(config: AppConfig) -> AcceptanceCheckResult:
    try:
        points = load_collection_points(config.project_root / "config" / "collection_points.json")
    except Exception as exc:
        return AcceptanceCheckResult(
            "QA-15",
            "Pontos de coleta",
            "failed",
            "config/collection_points.json",
            f"Falha ao carregar pontos de coleta: {exc}",
        )

    covered_classes = {
        class_id
        for point in points
        for class_id in point.accepted_classes
        if class_id in config.classes
    }
    special_points = filter_collection_points(points, class_id="battery")
    minimum_covered = {"plastic", "paper_cardboard", "metal", "glass", "battery", "electronic"}
    status = "ok" if points and minimum_covered.issubset(covered_classes) and special_points else "attention"
    details = (
        f"{len(points)} ponto(s) cadastrados; classes cobertas: {', '.join(sorted(covered_classes))}."
        if points
        else "Nenhum ponto cadastrado na base local."
    )
    return AcceptanceCheckResult(
        "QA-15",
        "Pontos de coleta",
        status,
        "config/collection_points.json; src/ecoscan/disposal/collection_points.py",
        details,
    )


def _check_invalid_image_rejection(config: AppConfig) -> AcceptanceCheckResult:
    with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_file:
        try:
            validate_image_file(
                temp_file.name,
                allowed_extensions=config.allowed_extensions,
                min_size=config.min_image_size,
            )
        except ImageValidationError:
            return AcceptanceCheckResult(
                "QA-03",
                "Validação",
                "ok",
                "src/ecoscan/image_processing/validation.py",
                "Arquivo vazio foi rejeitado corretamente.",
            )
    return AcceptanceCheckResult(
        "QA-03",
        "Validação",
        "failed",
        "src/ecoscan/image_processing/validation.py",
        "Arquivo vazio não foi rejeitado.",
    )


def _check_error_contract() -> AcceptanceCheckResult:
    payload = public_error_payload(ImageValidationError("Image file is empty."))
    expected_keys = {"ok", "code", "title", "error", "message", "action", "category"}
    missing = sorted(expected_keys - set(payload))
    catalog_codes = {item.code for item in error_catalog()}
    catalog_ok = {"IMG-001", "MODEL-001", "CAM-001"}.issubset(catalog_codes)
    status = (
        "ok"
        if payload.get("code") == "IMG-001" and not missing and "technical_detail" not in payload and catalog_ok
        else "failed"
    )
    details = (
        "Contrato público contém código, título, mensagem, ação, categoria e catálogo de erros principais."
        if status == "ok"
        else "Contrato incompleto; faltando: " + ", ".join(missing or ["códigos principais no catálogo"])
    )
    return AcceptanceCheckResult(
        "QA-10",
        "Erros",
        status,
        "src/ecoscan/errors.py",
        details,
    )


def _check_device_interface(config: AppConfig) -> AcceptanceCheckResult:
    streamlit_path = config.project_root / "src" / "ecoscan" / "ui" / "streamlit_app.py"
    live_path = config.project_root / "src" / "ecoscan" / "live_camera" / "server.py"
    try:
        streamlit_text = streamlit_path.read_text(encoding="utf-8")
        live_text = live_path.read_text(encoding="utf-8")
    except OSError as exc:
        return AcceptanceCheckResult(
            "QA-11",
            "Interface",
            "failed",
            "src/ecoscan/ui e src/ecoscan/live_camera",
            f"Falha ao ler arquivos de interface: {exc}",
        )

    expected = [
        "ecoscan-status-strip" in streamlit_text,
        "_render_probability_bars" in streamlit_text,
        "_render_disposal_action_panel" in streamlit_text,
        "_render_collection_points_tab" in streamlit_text,
        "_render_environmental_impact" in streamlit_text,
        "_render_segmentation_decision" in streamlit_text,
        '["auto", "none", "otsu", "hsv_color", "grabcut"]' in streamlit_text,
        "_render_live_camera_link" in streamlit_text,
        "_render_photo_requirement_plan" in streamlit_text,
        "_render_campaign_tab" in streamlit_text,
        "_render_civic_reports_tab" in streamlit_text,
        "_render_account_tab" in streamlit_text,
        "_render_admin_tab" in streamlit_text,
        "Perfil ativo" in streamlit_text,
        "ecoscan-recycle-visual" in streamlit_text,
        "_hero_recycle_visual" in streamlit_text,
        "Escanear com câmera traseira" in streamlit_text,
        "Escaneie. Recicle. Pontue." in streamlit_text,
        'analysis_tab = "Escanear"' in streamlit_text,
        'collection_tab = "Mapa"' in streamlit_text,
        "_render_public_app_chrome" in streamlit_text,
        "_render_public_overview_strip" in streamlit_text,
        "[data-testid=\"stSidebar\"]" in streamlit_text,
        "score-ring" in live_text,
        "targetPanel" in live_text,
        "probabilities" in live_text,
        "environmental_impact" in live_text,
        'let facingMode = "environment";' in live_text,
        "facingMode = { exact: mode }" in live_text,
        "facingMode = { ideal: mode }" in live_text,
        "câmera ativa; traseira não confirmada" in live_text,
    ]
    return AcceptanceCheckResult(
        "QA-11",
        "Interface",
        "ok" if all(expected) else "attention",
        "streamlit_app.py e live_camera/server.py",
        "Interface possui resumo executivo, perfis, campanha, denúncia, conta, gestão, link live, barras de confiança, destino visual, impacto ambiental, busca no mapa, painel mobile e prioridade verificável para câmera traseira." if all(expected) else "Interface visual parcialmente aplicada.",
    )


def _check_campaign_and_reports(config: AppConfig) -> AcceptanceCheckResult:
    try:
        campaign = load_campaign(config.project_root / "config" / "campaigns.json")
    except Exception as exc:
        return AcceptanceCheckResult(
            "QA-16",
            "Campanha e denúncias",
            "failed",
            "config/campaigns.json",
            f"Falha ao carregar campanha: {exc}",
        )

    report_service = config.project_root / "src" / "ecoscan" / "services" / "civic_reports.py"
    mission_count = len(campaign.missions)
    reward_count = len(campaign.rewards)
    status = "ok" if mission_count >= 4 and reward_count >= 2 and report_service.exists() else "attention"
    return AcceptanceCheckResult(
        "QA-16",
        "Campanha e denúncias",
        status,
        "config/campaigns.json; src/ecoscan/services/campaigns.py; src/ecoscan/services/civic_reports.py",
        f"{mission_count} missão(ões), {reward_count} recompensa(s) e triagem de denúncia por imagem configuradas.",
    )


def _check_accounts_and_admin(config: AppConfig) -> AcceptanceCheckResult:
    try:
        profiles = load_user_profiles(profiles_path_from_config(config))
    except Exception as exc:
        return AcceptanceCheckResult(
            "QA-17",
            "Perfis e gestão",
            "failed",
            "config/user_profiles.json; src/ecoscan/services/accounts.py",
            f"Falha ao carregar perfis: {exc}",
        )

    streamlit_text = (config.project_root / "src" / "ecoscan" / "ui" / "streamlit_app.py").read_text(
        encoding="utf-8"
    )
    account_service = config.project_root / "src" / "ecoscan" / "services" / "accounts.py"
    has_user = any(profile.role == "user" for profile in profiles)
    has_admin = any(profile.role == "admin" for profile in profiles)
    ui_ok = all(
        marker in streamlit_text
        for marker in [
            "_render_account_tab",
            "_render_admin_tab",
            "points_ledger_path_from_config",
            "append_point_transaction",
            "append_civic_report_review",
        ]
    )
    status = "ok" if has_user and has_admin and account_service.exists() and ui_ok else "attention"
    return AcceptanceCheckResult(
        "QA-17",
        "Perfis e gestão",
        status,
        "config/user_profiles.json; src/ecoscan/services/accounts.py; src/ecoscan/ui/streamlit_app.py",
        f"{len(profiles)} perfil(is) ativo(s), com usuário={has_user}, admin={has_admin}, pontos persistentes e revisão administrativa.",
    )


def _check_model_and_pipeline(
    config: AppConfig,
    report_dir: Path,
    sample_image: Path | None,
) -> list[AcceptanceCheckResult]:
    checks: list[AcceptanceCheckResult] = []
    selected_model = model_status(config)
    if selected_model.selected_kind == "none":
        return [
            AcceptanceCheckResult(
                "QA-04",
                "Modelo",
                "pending",
                "models/baseline_classifier.json, models/vision_classifier.npz ou models/ecoscan_transfer.keras",
                "Nenhum modelo disponível para inferência.",
            )
        ]

    checks.append(
        AcceptanceCheckResult(
            "QA-04",
            "Modelo",
            "ok",
            selected_model.selected_path,
            f"Modelo selecionado: {selected_model.selected_kind}.",
        )
    )

    if sample_image is None:
        checks.append(
            AcceptanceCheckResult(
                "QA-05",
                "Inferência",
                "pending",
                "data/raw",
                "Nenhuma imagem de amostra encontrada para smoke test.",
            )
        )
        return checks

    try:
        bundle = load_model_bundle_for_analysis(config)
        result = analyze_waste_image(
            sample_image,
            config,
            options=ProcessingPipelineOptions(filter_name="auto", segmentation_name="auto"),
            model_bundle=bundle,
        )
        artifacts = save_pipeline_artifacts(result.pipeline, report_dir / "sample_inference")
        checks.append(
            AcceptanceCheckResult(
                "QA-05",
                "Inferência",
                "ok" if result.top_class else "failed",
                str(sample_image),
                (
                    f"Classe mais provável: {result.top_class}; aceita: {result.predicted_class or '__uncertain__'}; "
                    f"score: {_format_score(result.probability)}."
                ),
            )
        )
        checks.append(
            AcceptanceCheckResult(
                "QA-06",
                "Pipeline",
                "ok" if _pipeline_has_expected_metadata(result.pipeline.metadata) else "failed",
                str(artifacts[-1]),
                (
                    f"Filtro: {result.pipeline.metadata['filter']['name']}; "
                    f"sequência: {result.pipeline.metadata['filter']['decision'].get('selected')}; "
                    f"segmentação: {result.pipeline.metadata['segmentation']['name']}; "
                    f"decisão: {result.pipeline.metadata['segmentation']['decision']['selected']}; "
                    f"captura: {result.pipeline.metadata['capture_quality']['status']}; "
                    f"elementos: {result.pipeline.element_analysis.significant_count}."
                ),
            )
        )
        live_payload = LiveCameraAnalyzer(config, model_bundle=bundle).analyze_frame(sample_image.read_bytes())
        detections = live_payload.get("detections", [])
        checks.append(
            AcceptanceCheckResult(
                "QA-07",
                "Câmera ao vivo",
                "ok" if live_payload.get("ok") else "failed",
                "src/ecoscan/live_camera",
                f"Frame analisado; detecções rastreadas: {len(detections)}.",
            )
        )
    except Exception as exc:
        checks.append(
            AcceptanceCheckResult(
                "QA-05",
                "Inferência",
                "failed",
                str(sample_image),
                f"Falha no smoke test: {exc}",
            )
        )
    return checks


def _check_dataset_readiness(config: AppConfig) -> AcceptanceCheckResult:
    summary, _ = build_dataset_readiness(config, target_per_class=50)
    return AcceptanceCheckResult(
        "QA-08",
        "Dataset",
        "ok" if summary.ready_for_final_training else "attention",
        "reports/dataset_readiness/dataset_readiness.md",
        (
            f"Raw: {summary.raw_total}; curado: {summary.curated_total}; "
            f"faltam imagens brutas: {summary.missing_raw_total}."
        ),
    )


def _check_final_model(config: AppConfig) -> AcceptanceCheckResult:
    selected_model = model_status(config)
    return AcceptanceCheckResult(
        "QA-09",
        "Modelo final",
        "ok" if selected_model.final_model_exists else "pending",
        selected_model.final_model_path,
        "Modelo final encontrado." if selected_model.final_model_exists else "Aguardando dataset curado e treino final.",
    )


def _pipeline_has_expected_metadata(metadata: dict[str, Any]) -> bool:
    return all(
        key in metadata
        for key in ("quality", "filter", "segmentation", "elements", "capture_quality", "model_input_shape")
    )


def _find_sample_image(config: AppConfig) -> Path | None:
    for class_id in config.classes:
        class_dir = config.directories["raw_data"] / class_id
        if not class_dir.exists():
            continue
        for path in sorted(class_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in config.allowed_extensions:
                return path
    return None


def _format_score(value: float | None) -> str:
    if value is None:
        return "indisponível"
    return f"{value:.3f}"


def _summarize(checks: Iterable[AcceptanceCheckResult]) -> dict[str, int]:
    summary: dict[str, int] = {"ok": 0, "attention": 0, "pending": 0, "failed": 0}
    for check in checks:
        summary[check.status] = summary.get(check.status, 0) + 1
    summary["total"] = sum(value for key, value in summary.items() if key != "total")
    return summary


def _write_report(report: AcceptanceCheckReport, report_dir: Path) -> None:
    (report_dir / "acceptance_checks.json").write_text(
        json.dumps(asdict(report), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_csv(report_dir / "acceptance_checks.csv", report.checks)
    (report_dir / "acceptance_checks.md").write_text(_format_markdown(report), encoding="utf-8")


def _write_csv(path: Path, rows: Iterable[AcceptanceCheckResult]) -> None:
    rows = list(rows)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["code", "area", "status", "evidence", "details"])
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _format_markdown(report: AcceptanceCheckReport) -> str:
    summary = report.summary
    lines = [
        "# Validação de aceite - EcoScan",
        "",
        f"Gerado em UTC: `{report.generated_at_utc}`.",
        "",
        "## Resumo",
        "",
        f"- OK: {summary.get('ok', 0)}.",
        f"- Atenção: {summary.get('attention', 0)}.",
        f"- Pendente: {summary.get('pending', 0)}.",
        f"- Falha: {summary.get('failed', 0)}.",
        "",
        "## Checks",
        "",
        "| Código | Área | Status | Evidência | Detalhes |",
        "|---|---|---:|---|---|",
    ]
    for check in report.checks:
        lines.append(
            f"| {check.code} | {check.area} | {check.status} | `{check.evidence}` | {check.details} |"
        )
    lines.append("")
    return "\n".join(lines)
