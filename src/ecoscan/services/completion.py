from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ecoscan.config import AppConfig
from ecoscan.services.aps_audit import build_aps_audit, summarize_audit
from ecoscan.services.dataset_governance import build_dataset_readiness
from ecoscan.services.diagnostics import model_status


@dataclass(frozen=True)
class CompletionAction:
    area: str
    title: str
    status: str
    priority: str
    evidence: str
    detail: str
    next_step: str


@dataclass(frozen=True)
class CompletionPlan:
    readiness_score: float
    ready_for_demo: bool
    ready_for_final_training: bool
    final_model_exists: bool
    selected_model_kind: str
    acceptance_ok: int
    acceptance_attention: int
    acceptance_pending: int
    acceptance_failed: int
    raw_total: int
    curated_total: int
    missing_raw_total: int
    missing_curated_total: int
    actions: tuple[CompletionAction, ...]


def _acceptance_summary(config: AppConfig) -> dict[str, int]:
    path = config.directories["reports"] / "acceptance_checks" / "acceptance_checks.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ok": 0, "attention": 0, "pending": 0, "failed": 0, "total": 0}

    summary = payload.get("summary", {})
    return {
        "ok": int(summary.get("ok", 0)),
        "attention": int(summary.get("attention", 0)),
        "pending": int(summary.get("pending", 0)),
        "failed": int(summary.get("failed", 0)),
        "total": int(summary.get("total", 0)),
    }


def _status_for_file(path: Path) -> str:
    return "ok" if path.exists() else "attention"


def _missing_raw_detail(rows: object) -> str:
    missing = [
        f"{row.display_name}: {row.missing_raw}"
        for row in rows
        if row.missing_raw > 0
    ]
    if not missing:
        return "Todas as classes já alcançaram o alvo bruto mínimo."
    return "Ainda faltam imagens brutas em: " + "; ".join(missing) + "."


def build_completion_plan(config: AppConfig) -> CompletionPlan:
    audit_summary = summarize_audit(build_aps_audit(config))
    dataset_summary, dataset_rows = build_dataset_readiness(config, target_per_class=50)
    selected_model = model_status(config)
    acceptance = _acceptance_summary(config)

    readiness_score = float(audit_summary["readiness_score"])
    ready_for_demo = (
        acceptance.get("failed", 0) == 0
        and selected_model.selected_kind != "none"
        and readiness_score >= 70.0
    )
    pack_index = config.directories["reports"] / "delivery_pack" / "indice_entrega.md"
    academic_report = config.directories["reports"] / "aps_report" / "relatorio_aps.md"

    actions = [
        CompletionAction(
            area="Produto",
            title="Fluxo principal pronto para demonstração",
            status="ok" if ready_for_demo else "attention",
            priority="alta",
            evidence="Interface, câmera, pipeline, orientação e aceite automatizado.",
            detail=(
                "O produto pode ser demonstrado com transparência acadêmica."
                if ready_for_demo
                else "Revise falhas de aceite, modelo ativo ou score de prontidão antes de apresentar."
            ),
            next_step="Ensaiar com uma imagem boa, uma ruim, uma captura de câmera e a aba de processamento.",
        ),
        CompletionAction(
            area="Dados",
            title="Base bruta mínima por classe",
            status="ok" if dataset_summary.missing_raw_total == 0 else "attention",
            priority="alta",
            evidence="reports/dataset_readiness/dataset_readiness.md",
            detail=_missing_raw_detail(dataset_rows),
            next_step="Completar as classes com faltas e manter variações de ângulo, fundo, iluminação e estado do resíduo.",
        ),
        CompletionAction(
            area="Dados",
            title="Curadoria pronta para treino final",
            status="ok" if dataset_summary.ready_for_final_training else "attention",
            priority="alta",
            evidence="data/curated; reports/dataset_review/review_sheet.csv",
            detail=(
                f"{dataset_summary.curated_total} imagens curadas; "
                f"faltam {dataset_summary.missing_curated_total} imagens curadas para o alvo final."
            ),
            next_step="Revisar imagens, remover ruído/duplicatas e preencher data/curated antes do transfer learning.",
        ),
        CompletionAction(
            area="Modelo",
            title="Modelo final por transfer learning",
            status="ok" if selected_model.final_model_exists else "pending",
            priority="alta",
            evidence=selected_model.final_model_path,
            detail=(
                "Modelo final carregável encontrado."
                if selected_model.final_model_exists
                else "A aplicação usa o modelo inicial até existir dataset curado e treino final."
            ),
            next_step="Após curadoria, rodar treino, avaliar contra a baseline e promover apenas se superar as métricas.",
        ),
        CompletionAction(
            area="Qualidade",
            title="Validação de aceite sem falhas",
            status="failed" if acceptance.get("failed", 0) else ("ok" if acceptance.get("total", 0) else "attention"),
            priority="alta",
            evidence="reports/acceptance_checks/acceptance_checks.md",
            detail=(
                f"{acceptance.get('ok', 0)} ok, {acceptance.get('attention', 0)} atenção, "
                f"{acceptance.get('pending', 0)} pendente, {acceptance.get('failed', 0)} falha."
            ),
            next_step="Rodar scripts/run_acceptance_checks.py antes da entrega final e anexar o relatório atualizado.",
        ),
        CompletionAction(
            area="Entrega",
            title="Pacote técnico e relatório acadêmico",
            status="ok" if pack_index.exists() and academic_report.exists() else "attention",
            priority="média",
            evidence="reports/delivery_pack; reports/aps_report/relatorio_aps.md",
            detail=(
                "Relatório e pacote de entrega encontrados."
                if pack_index.exists() and academic_report.exists()
                else "Gere o relatório acadêmico e o pacote técnico antes de entregar."
            ),
            next_step="Rodar scripts/generate_academic_report.py e scripts/prepare_delivery_pack.py após as últimas alterações.",
        ),
        CompletionAction(
            area="Operação",
            title="Uso diário pela Secretaria e pelo cidadão",
            status="ok",
            priority="média",
            evidence="Perfis, campanha, denúncia, pontos de coleta e painel de gestão.",
            detail="A experiência já separa o fluxo cidadão do fluxo administrativo da gestão ambiental.",
            next_step="Validar textos, pontos oficiais e regras locais antes de um uso institucional real.",
        ),
    ]

    return CompletionPlan(
        readiness_score=readiness_score,
        ready_for_demo=ready_for_demo,
        ready_for_final_training=dataset_summary.ready_for_final_training,
        final_model_exists=selected_model.final_model_exists,
        selected_model_kind=selected_model.selected_kind,
        acceptance_ok=acceptance.get("ok", 0),
        acceptance_attention=acceptance.get("attention", 0),
        acceptance_pending=acceptance.get("pending", 0),
        acceptance_failed=acceptance.get("failed", 0),
        raw_total=dataset_summary.raw_total,
        curated_total=dataset_summary.curated_total,
        missing_raw_total=dataset_summary.missing_raw_total,
        missing_curated_total=dataset_summary.missing_curated_total,
        actions=tuple(actions),
    )


def format_completion_markdown(plan: CompletionPlan) -> str:
    demo_text = "sim" if plan.ready_for_demo else "não"
    final_text = "sim" if plan.ready_for_final_training and plan.final_model_exists else "não"
    lines = [
        "# Checklist de conclusão - EcoScan",
        "",
        f"- Pronto para demonstração controlada: {demo_text}.",
        f"- Pronto como reconhecimento final treinado: {final_text}.",
        f"- Score de prontidão: {plan.readiness_score}%.",
        f"- Modelo ativo: {plan.selected_model_kind}.",
        f"- Aceite: {plan.acceptance_ok} ok, {plan.acceptance_attention} atenção, {plan.acceptance_pending} pendente, {plan.acceptance_failed} falha.",
        f"- Dataset: {plan.raw_total} imagens brutas, {plan.curated_total} curadas.",
        "",
        "| Área | Item | Status | Prioridade | Próximo passo |",
        "|---|---|---:|---:|---|",
    ]
    for action in plan.actions:
        lines.append(
            "| "
            f"{action.area} | {action.title} | {action.status} | {action.priority} | {action.next_step} |"
        )
    lines.extend(
        [
            "",
            "## Leitura correta",
            "",
            "O sistema está próximo de pronto para apresentação e uso demonstrativo. "
            "A etapa que ainda não deve ser vendida como final é o reconhecimento definitivo, "
            "porque depende de dataset curado e modelo final treinado.",
            "",
        ]
    )
    return "\n".join(lines)
