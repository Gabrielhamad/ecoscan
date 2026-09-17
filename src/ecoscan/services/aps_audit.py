from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ecoscan.config import AppConfig
from ecoscan.services.diagnostics import dataset_status, dependency_status, model_status


@dataclass(frozen=True)
class AuditItem:
    code: str
    area: str
    requirement: str
    status: str
    priority: str
    evidence: str
    rationale: str
    next_action: str


def _exists(config: AppConfig, relative_path: str) -> bool:
    return (config.project_root / relative_path).exists()


def _dependency_map() -> dict[str, bool]:
    return {item.name.lower(): item.installed for item in dependency_status()}


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _status_for_evidence(config: AppConfig, paths: list[str]) -> str:
    return "ok" if all(_exists(config, path) for path in paths) else "pending"


def _minimum_count(counts: dict[str, int]) -> int:
    return min(counts.values()) if counts else 0


def _dataset_volume_item(config: AppConfig) -> AuditItem:
    status = dataset_status(config)
    min_raw = _minimum_count(status.raw_counts)
    total_raw = sum(status.raw_counts.values())
    target = max(50, config.min_images_per_class_warning)
    if min_raw >= target:
        gate_status = "ok"
        next_action = "Prosseguir para curadoria, split e treinamento final."
    elif min_raw >= config.min_images_per_class_warning:
        gate_status = "attention"
        next_action = f"Coletar mais imagens até pelo menos {target} por classe antes do modelo final."
    else:
        gate_status = "pending"
        next_action = f"Completar dataset bruto; classe mais fraca tem {min_raw} imagem(ns)."

    return AuditItem(
        code="APS-DATA-01",
        area="Dataset",
        requirement="Quantidade mínima e balanceamento por classe.",
        status=gate_status,
        priority="alta",
        evidence="data/raw e reports/dataset_analysis",
        rationale=f"Dataset bruto tem {total_raw} imagens; menor classe tem {min_raw}; alvo profissional: {target}.",
        next_action=next_action,
    )


def _dataset_curation_item(config: AppConfig) -> AuditItem:
    status = dataset_status(config)
    curated_total = sum(status.curated_counts.values())
    if curated_total > 0:
        gate_status = "ok"
        rationale = f"Dataset curado contém {curated_total} imagens."
        next_action = "Manter revisão antes de cada split."
    else:
        gate_status = "attention"
        rationale = "A estrutura de revisão existe, mas o dataset curado ainda está vazio."
        next_action = "Após coletar imagens do grupo, preencher a planilha e aplicar a curadoria."

    return AuditItem(
        code="APS-DATA-02",
        area="Dataset",
        requirement="Curadoria antes de treino final para reduzir ruído e vazamento.",
        status=gate_status,
        priority="alta",
        evidence="reports/dataset_review/review_sheet.csv e data/curated",
        rationale=rationale,
        next_action=next_action,
    )


def _baseline_quality_item(config: AppConfig) -> AuditItem:
    metrics_path = config.directories["reports"] / "evaluation" / "baseline_test" / "metrics.json"
    metrics = _load_json(metrics_path)
    macro_f1 = metrics.get("macro_f1")
    accuracy = metrics.get("accuracy")
    uncertain_count = metrics.get("uncertain_count")
    total = metrics.get("total")

    if not metrics:
        return AuditItem(
            code="APS-MODEL-02",
            area="Modelo",
            requirement="Baseline avaliada com métricas além de accuracy.",
            status="pending",
            priority="alta",
            evidence="reports/evaluation/baseline_test/metrics.json",
            rationale="Métricas da baseline ainda não foram geradas.",
            next_action="Rodar evaluate_model.py para gerar métricas e matriz de confusão.",
        )

    if isinstance(macro_f1, int | float) and macro_f1 >= 0.5:
        gate_status = "ok"
        next_action = "Usar como referência comparativa para o modelo final."
    else:
        gate_status = "attention"
        next_action = "Tratar a baseline como evidência acadêmica, não como desempenho final."

    return AuditItem(
        code="APS-MODEL-02",
        area="Modelo",
        requirement="Baseline avaliada com accuracy, precision, recall, F1 e matriz de confusão.",
        status=gate_status,
        priority="alta",
        evidence="reports/evaluation/baseline_test/metrics.json",
        rationale=(
            f"accuracy={accuracy}, macro_f1={macro_f1}, "
            f"incertas={uncertain_count}/{total}."
        ),
        next_action=next_action,
    )


def _final_model_item(config: AppConfig) -> AuditItem:
    selected = model_status(config)
    if selected.final_model_exists:
        return AuditItem(
            code="APS-MODEL-03",
            area="Modelo",
            requirement="Modelo final por transfer learning salvo e carregável.",
            status="ok",
            priority="alta",
            evidence=selected.final_model_path,
            rationale="Modelo final encontrado.",
            next_action="Avaliar no split de teste e comparar com a baseline.",
        )
    return AuditItem(
        code="APS-MODEL-03",
        area="Modelo",
        requirement="Modelo final por transfer learning salvo e carregável.",
        status="pending",
        priority="alta",
        evidence=selected.final_model_path,
        rationale="Projeto está preparado, mas o arquivo .keras ainda não existe.",
        next_action="Treinar MobileNetV2 após dataset curado e ambiente TensorFlow disponível.",
    )


def _dependencies_item() -> AuditItem:
    dependencies = _dependency_map()
    missing = [
        name
        for name in ("opencv", "scikit-image", "tensorflow")
        if not dependencies.get(name, False)
    ]
    if not missing:
        gate_status = "ok"
        rationale = "Dependências principais e opcionais encontradas."
        next_action = "Manter ambiente congelado antes da apresentação."
    else:
        gate_status = "attention"
        rationale = f"Dependências ausentes: {', '.join(missing)}."
        next_action = "Instalar dependências opcionais antes de demonstrar webcam direta, GrabCut/HSV e treino final."
    return AuditItem(
        code="APS-OPS-01",
        area="Ambiente",
        requirement="Ambiente local com dependências para interface, processamento e treinamento.",
        status=gate_status,
        priority="média",
        evidence="requirements.txt, pyproject.toml e reports/diagnostics.json",
        rationale=rationale,
        next_action=next_action,
    )


def build_aps_audit(config: AppConfig) -> list[AuditItem]:
    fixed_items = [
        AuditItem(
            "APS-REQ-01",
            "Arquitetura",
            "Separação entre interface, processamento, segmentação, classificação, orientação e serviços.",
            _status_for_evidence(
                config,
                [
                    "src/ecoscan/ui/streamlit_app.py",
                    "src/ecoscan/image_processing/preprocessing.py",
                    "src/ecoscan/image_processing/quality.py",
                    "src/ecoscan/segmentation/methods.py",
                    "src/ecoscan/segmentation/elements.py",
                    "src/ecoscan/classification/inference.py",
                    "src/ecoscan/disposal/guidance.py",
                ],
            ),
            "alta",
            "src/ecoscan/*",
            "Projeto está dividido em módulos coerentes com o manual da APS.",
            "Manter novas funções dentro dos módulos existentes.",
        ),
        AuditItem(
            "APS-IMG-01",
            "Aquisição",
            "Upload, câmera, detecção por captura e validação de imagem com tratamento de erro.",
            _status_for_evidence(
                config,
                [
                    "src/ecoscan/ui/streamlit_app.py",
                    "scripts/capture_webcam.py",
                    "src/ecoscan/image_processing/validation.py",
                ],
            ),
            "alta",
            "streamlit_app.py, capture_webcam.py, validation.py",
            "Upload e câmera executam o mesmo pipeline de detecção; validação cobre extensão, arquivo vazio, corrupção e tamanho.",
            "Testar câmera no notebook/computador da apresentação.",
        ),
        AuditItem(
            "APS-LIVE-01",
            "Câmera ao vivo",
            "Câmera traseira mobile, reconhecimento periódico de frames e tracking visual.",
            _status_for_evidence(
                config,
                [
                    "src/ecoscan/live_camera/server.py",
                    "src/ecoscan/live_camera/analyzer.py",
                    "src/ecoscan/live_camera/tracking.py",
                    "scripts/run_live_camera_app.py",
                ],
            ),
            "alta",
            "src/ecoscan/live_camera e scripts/run_live_camera_app.py",
            "Modo ao vivo prioriza câmera traseira no navegador, envia frames ao backend e desenha caixas com IDs por componente segmentado.",
            "Testar em celular real; usar HTTPS ou túnel seguro se o navegador bloquear câmera em IP local.",
        ),
        AuditItem(
            "APS-PROC-01",
            "Processamento",
            "Pipeline reproduzível com redimensionamento, normalização, filtragem adaptativa, parâmetros e diagnóstico de qualidade.",
            _status_for_evidence(
                config,
                [
                    "src/ecoscan/app/pipeline.py",
                    "src/ecoscan/image_processing/adaptive_filters.py",
                    "src/ecoscan/image_processing/filters.py",
                    "src/ecoscan/image_processing/capture_quality.py",
                    "src/ecoscan/image_processing/quality.py",
                    "reports/filter_experiments/metal_can/filter_comparison.jpg",
                ],
            ),
            "alta",
            "src/ecoscan/app/pipeline.py e reports/filter_experiments",
            "Sequências de filtros, parâmetros, métricas e orientação de recaptura podem ser demonstrados sem ficar presos a uma técnica única.",
            "Registrar novos experimentos quando o dataset do grupo chegar.",
        ),
        AuditItem(
            "APS-SEG-01",
            "Segmentação",
            "Segmentação modular, demonstrável e acompanhada de análise de componentes visuais.",
            _status_for_evidence(
                config,
                [
                    "src/ecoscan/segmentation/methods.py",
                    "src/ecoscan/segmentation/elements.py",
                    "reports/segmentation_experiments/metal_can/segmentation_comparison.jpg",
                ],
            ),
            "alta",
            "src/ecoscan/segmentation e reports/segmentation_experiments",
            "Otsu funciona sem OpenCV; HSV e GrabCut ficam disponíveis quando OpenCV está instalado; componentes conectados explicam a máscara.",
            "Comparar impacto da segmentação no dataset real antes de fixar como padrão.",
        ),
        AuditItem(
            "APS-DATA-00",
            "Dataset",
            "Entrada controlada de novas imagens, manifesto e bloqueio de duplicatas exatas.",
            _status_for_evidence(
                config,
                [
                    "src/ecoscan/services/dataset_ingestion.py",
                    "scripts/ingest_dataset_folder.py",
                    "reports/dataset_uploads/upload_manifest.csv",
                ],
            ),
            "alta",
            "dataset_ingestion.py e reports/dataset_uploads/upload_manifest.csv",
            "Uploads entram no dataset bruto e ficam rastreáveis antes de treino.",
            "Usar o manifesto para explicar origem e qualidade das imagens adicionadas.",
        ),
        _dataset_volume_item(config),
        _dataset_curation_item(config),
        AuditItem(
            "APS-MODEL-01",
            "Modelo",
            "Baseline funcional antes do modelo final.",
            _status_for_evidence(config, ["models/baseline_classifier.json"]),
            "alta",
            "models/baseline_classifier.json",
            "Baseline KNN existe e permite demonstrar evolução futura.",
            "Não vender a baseline como modelo final; usar como comparação acadêmica.",
        ),
        _baseline_quality_item(config),
        _final_model_item(config),
        AuditItem(
            "APS-UX-01",
            "Interface",
            "Tela de análise, processamento, dataset, histórico e status.",
            _status_for_evidence(config, ["src/ecoscan/ui/streamlit_app.py"]),
            "média",
            "src/ecoscan/ui/streamlit_app.py",
            "Interface Streamlit cobre demonstração de usuário e explicação técnica.",
            "Fazer ensaio manual com imagens boas, ruins e fora do domínio.",
        ),
        AuditItem(
            "APS-UX-02",
            "Interface",
            "Uso em dispositivo com leitura visual moderna, controles tocáveis e feedback de confiança.",
            _status_for_evidence(
                config,
                [
                    "src/ecoscan/ui/streamlit_app.py",
                    "src/ecoscan/live_camera/server.py",
                ],
            ),
            "média",
            "streamlit_app.py e live_camera/server.py",
            "A interface mostra resumo executivo, link para modo live, barras de confiança, snapshot de qualidade e painel mobile no EcoScan Live.",
            "Validar em celular real antes da apresentação.",
        ),
        AuditItem(
            "APS-CIVIC-01",
            "Campanha",
            "Fluxo institucional com campanha, perfis, missões, pontos, recompensas e denúncia de mau descarte.",
            _status_for_evidence(
                config,
                [
                    "config/user_profiles.json",
                    "config/campaigns.json",
                    "src/ecoscan/services/accounts.py",
                    "src/ecoscan/services/campaigns.py",
                    "src/ecoscan/services/civic_reports.py",
                    "src/ecoscan/ui/streamlit_app.py",
                ],
            ),
            "média",
            "config/user_profiles.json; config/campaigns.json; src/ecoscan/services/accounts.py; src/ecoscan/services/civic_reports.py",
            "A proposta deixa de ser apenas um classificador e passa a incluir educação ambiental, participação do usuário, pontuação persistente e revisão administrativa pela gestão pública.",
            "Validar regras reais de recompensa, autenticação e encaminhamento com a instituição responsável.",
        ),
        AuditItem(
            "APS-LOG-01",
            "Logs",
            "Registro técnico de inferências, parâmetros e falhas sem expor stack trace ao usuário.",
            _status_for_evidence(
                config,
                [
                    "src/ecoscan/utils/logging_config.py",
                    "src/ecoscan/services/analysis_service.py",
                ],
            ),
            "média",
            "logs/ecoscan.log e analysis_service.py",
            "Inferências registram modelo, classe, score, filtro, segmentação e tempo de processamento.",
            "Revisar o log antes da apresentação para escolher exemplos bons e ruins.",
        ),
        AuditItem(
            "APS-ERR-01",
            "Erros",
            "Tratamento padronizado de erros com código, mensagem amigável, ação recomendada e log técnico.",
            _status_for_evidence(
                config,
                [
                    "src/ecoscan/errors.py",
                    "src/ecoscan/ui/streamlit_app.py",
                    "src/ecoscan/live_camera/server.py",
                    "docs/tratamento_erros.md",
                    "tests/test_error_handling.py",
                ],
            ),
            "média",
            "src/ecoscan/errors.py, docs/tratamento_erros.md, streamlit_app.py, live_camera/server.py e tests/test_error_handling.py",
            "Erros conhecidos são apresentados ao usuário com código e orientação, enquanto detalhes técnicos ficam controlados para log/diagnóstico.",
            "Manter novos fluxos usando o contrato central de erros.",
        ),
        AuditItem(
            "APS-QA-01",
            "Aceite",
            "Validação executável dos principais cenários da APS.",
            _status_for_evidence(
                config,
                [
                    "src/ecoscan/services/acceptance_checks.py",
                    "scripts/run_acceptance_checks.py",
                    "tests/test_error_handling.py",
                    "reports/acceptance_checks/acceptance_checks.md",
                ],
            ),
            "média",
            "reports/acceptance_checks",
            "Smoke test roda inferência real, pipeline, validação de imagem, contrato de erro, orientação e frame do modo ao vivo.",
            "Rodar antes da entrega e anexar o Markdown/CSV ao pacote de evidências.",
        ),
        AuditItem(
            "APS-DOC-01",
            "Documentação",
            "README, fluxo final, checklist, roadmap, pacote de entrega e documentação acadêmica.",
            _status_for_evidence(
                config,
                [
                    "README.md",
                    "docs/checklist_aps.md",
                    "docs/roadmap_profissional.md",
                    "docs/tratamento_erros.md",
                    "docs/relatorio_academico_base.md",
                    "docs/gestao_dataset_e_classes.md",
                    "docs/live_camera_mobile.md",
                    "src/ecoscan/services/delivery_pack.py",
                    "scripts/prepare_delivery_pack.py",
                    "src/ecoscan/services/acceptance_checks.py",
                    "scripts/run_acceptance_checks.py",
                ],
            ),
            "média",
            "README.md, docs/ e reports/delivery_pack",
            "Documentação cobre execução, justificativa, evidências, decisões e próximos passos.",
            "Gerar pacote de entrega antes do ensaio final.",
        ),
        _dependencies_item(),
        AuditItem(
            "APS-FUT-01",
            "Avançado",
            "Detecção treinada de múltiplas classes por objeto preparada como evolução, fora do MVP.",
            "future",
            "baixa",
            "src/ecoscan/detection/contracts.py",
            "Contrato futuro existe sem prometer YOLO antes de existir dataset anotado por caixas ou máscaras.",
            "Só avançar para YOLO após classificação simples ficar estável.",
        ),
    ]
    return fixed_items


def summarize_audit(items: list[AuditItem]) -> dict[str, object]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.status] = counts.get(item.status, 0) + 1
    score_scope = [item for item in items if item.status != "future"]
    ok_count = sum(1 for item in score_scope if item.status == "ok")
    score = round((ok_count / len(score_scope)) * 100, 1) if score_scope else 0.0
    high_priority_attention = [
        item.code for item in items
        if item.priority == "alta" and item.status in {"attention", "pending"}
    ]
    return {
        "counts": counts,
        "readiness_score": score,
        "high_priority_attention": high_priority_attention,
        "total_items": len(items),
    }


def format_audit_markdown(items: list[AuditItem]) -> str:
    summary = summarize_audit(items)
    lines = [
        "# Auditoria de engenharia do EcoScan",
        "",
        f"Score de prontidão: {summary['readiness_score']}% dos gates não futuros em `ok`.",
        "",
        "| Código | Área | Prioridade | Status | Requisito | Evidência | Próxima ação |",
        "|---|---|---:|---:|---|---|---|",
    ]
    for item in items:
        lines.append(
            "| "
            f"{item.code} | {item.area} | {item.priority} | {item.status} | "
            f"{item.requirement} | `{item.evidence}` | {item.next_action} |"
        )

    lines.extend(
        [
            "",
            "## Leituras principais",
            "",
            "- `ok`: item implementado ou demonstrável.",
            "- `attention`: funciona ou está estruturado, mas precisa de reforço antes da versão final.",
            "- `pending`: depende de dataset definitivo, ambiente ou treinamento.",
            "- `future`: fora do MVP atual.",
            "",
            "## Atenções de alta prioridade",
            "",
        ]
    )
    attention = [item for item in items if item.code in summary["high_priority_attention"]]
    if not attention:
        lines.append("- Nenhuma atenção alta pendente.")
    else:
        for item in attention:
            lines.append(f"- {item.code}: {item.rationale} Próxima ação: {item.next_action}")
    lines.append("")
    return "\n".join(lines)


def write_aps_audit_report(config: AppConfig, output_dir: str | Path | None = None) -> dict[str, Path]:
    report_dir = Path(output_dir).resolve() if output_dir else config.directories["reports"] / "project_audit"
    report_dir.mkdir(parents=True, exist_ok=True)
    items = build_aps_audit(config)
    summary = summarize_audit(items)

    json_path = report_dir / "aps_audit.json"
    markdown_path = report_dir / "aps_audit.md"
    payload = {
        "summary": summary,
        "items": [asdict(item) for item in items],
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown_path.write_text(format_audit_markdown(items), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}
