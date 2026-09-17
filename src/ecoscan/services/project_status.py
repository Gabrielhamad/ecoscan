from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ecoscan.config import AppConfig


@dataclass(frozen=True)
class StatusItem:
    area: str
    status: str
    evidence: str


def _exists(path: Path) -> str:
    return "ok" if path.exists() else "pending"


def build_project_status(config: AppConfig) -> list[StatusItem]:
    reports = config.directories["reports"]
    models = config.directories["models"]
    final_model = config.project_root / str(config.model.get("output_path", "models/ecoscan_transfer.keras"))
    return [
        StatusItem("aquisição por upload", "ok", "src/ecoscan/ui/streamlit_app.py"),
        StatusItem("aquisição por câmera", "ok", "Streamlit camera_input e scripts/capture_webcam.py"),
        StatusItem("detecção por câmera", "ok", "src/ecoscan/ui/streamlit_app.py e scripts/capture_webcam.py"),
        StatusItem("câmera ao vivo mobile", "ok", "src/ecoscan/live_camera/server.py e scripts/run_live_camera_app.py"),
        StatusItem("tracking visual ao vivo", "ok", "src/ecoscan/live_camera/tracking.py"),
        StatusItem("validação de imagem", "ok", "src/ecoscan/image_processing/validation.py"),
        StatusItem("pré-processamento", "ok", "src/ecoscan/image_processing/preprocessing.py"),
        StatusItem("filtros", "ok", "src/ecoscan/image_processing/filters.py"),
        StatusItem("filtragem adaptativa", "ok", "src/ecoscan/image_processing/adaptive_filters.py"),
        StatusItem("diagnóstico de qualidade da imagem", "ok", "src/ecoscan/image_processing/quality.py"),
        StatusItem("orientação de qualidade da captura", "ok", "src/ecoscan/image_processing/capture_quality.py"),
        StatusItem("segmentação adaptativa", "ok", "src/ecoscan/segmentation/adaptive.py e src/ecoscan/segmentation/methods.py"),
        StatusItem("análise de elementos segmentados", "ok", "src/ecoscan/segmentation/elements.py"),
        StatusItem("visualização do pipeline", "ok", "reports/processing_demo"),
        StatusItem("orientações de descarte", "ok", "config/disposal_guidance.json"),
        StatusItem("destino visual de descarte", "ok", "config/disposal_targets.json; assets/disposal_targets"),
        StatusItem("impacto ambiental do descarte", "ok", "config/environmental_impacts.json; src/ecoscan/disposal/impact.py"),
        StatusItem("perfis de usuário e admin", "ok", "config/user_profiles.json; src/ecoscan/services/accounts.py"),
        StatusItem("campanha ambiental", "ok", "config/campaigns.json; src/ecoscan/services/campaigns.py"),
        StatusItem("operação de campanha", "ok", "src/ecoscan/services/operations.py; aba Gestão"),
        StatusItem("missões e pontos persistentes", "ok", "src/ecoscan/services/accounts.py; src/ecoscan/ui/streamlit_app.py"),
        StatusItem("denúncia de mau descarte", "ok", "src/ecoscan/services/civic_reports.py; src/ecoscan/ui/streamlit_app.py"),
        StatusItem("painel administrativo", "ok", "src/ecoscan/ui/streamlit_app.py; reports/civic_reports/review_manifest.csv"),
        StatusItem("acesso para testes em grupo", "ok", "src/ecoscan/services/access_plan.py; aba Sistema"),
        StatusItem("registro de testes de campo", "ok", "src/ecoscan/services/field_testing.py; abas Perfil e Gestão"),
        StatusItem("hospedagem gratuita HTTPS", "ok", "streamlit_app.py; src/ecoscan/services/deployment_readiness.py; docs/hospedagem_gratuita.md"),
        StatusItem("busca de ponto próximo", "ok", "src/ecoscan/disposal/targets.py e src/ecoscan/ui/streamlit_app.py"),
        StatusItem("base local de pontos de coleta", "ok", "config/collection_points.json; src/ecoscan/disposal/collection_points.py"),
        StatusItem("histórico local", "ok", "src/ecoscan/services/history.py"),
        StatusItem("logging técnico", "ok", "logs/ecoscan.log e src/ecoscan/utils/logging_config.py"),
        StatusItem("tratamento de erros", "ok", "src/ecoscan/errors.py, docs/tratamento_erros.md e tests/test_error_handling.py"),
        StatusItem("decisão segura do reconhecimento", "ok", "src/ecoscan/services/recognition_safety.py; aba Escanear"),
        StatusItem("qualidade operacional do reconhecimento", "ok", "src/ecoscan/services/usage_quality.py; aba Gestão"),
        StatusItem("fluxo público mobile", "ok", "src/ecoscan/services/public_flow.py; aba Escanear"),
        StatusItem("plano de reforço do reconhecimento", "ok", "src/ecoscan/services/recognition_improvement.py; aba Gestão"),
        StatusItem("governança do modelo final", "ok", "src/ecoscan/services/model_governance.py; aba Conclusão"),
        StatusItem("upload de dataset", "ok", "src/ecoscan/services/dataset_ingestion.py"),
        StatusItem("plano de fotos por classe", "ok", "config/photo_requirements.json; src/ecoscan/services/photo_requirements.py"),
        StatusItem("manifesto de uploads", _exists(reports / "dataset_uploads" / "upload_manifest.csv"), "reports/dataset_uploads/upload_manifest.csv"),
        StatusItem("prontidão do dataset", _exists(reports / "dataset_readiness" / "dataset_readiness.md"), "reports/dataset_readiness/dataset_readiness.md"),
        StatusItem("análise exploratória", _exists(reports / "dataset_analysis" / "dataset_analysis.json"), "reports/dataset_analysis"),
        StatusItem("curadoria de dataset", _exists(reports / "dataset_review" / "review_sheet.csv"), "reports/dataset_review/review_sheet.csv"),
        StatusItem("preparação automática de imagens", _exists(reports / "dataset_preparation" / "preparation_manifest.csv"), "reports/dataset_preparation"),
        StatusItem("split treino/validação/teste", _exists(reports / "dataset_split" / "split_manifest.json"), "reports/dataset_split"),
        StatusItem("baseline", _exists(models / "baseline_classifier.json"), "models/baseline_classifier.json"),
        StatusItem("modelo visual supervisionado", _exists(models / "vision_svm_classifier.joblib"), "models/vision_svm_classifier.joblib"),
        StatusItem("modelo visual clássico", _exists(models / "vision_classifier.npz"), "models/vision_classifier.npz"),
        StatusItem("avaliação exportável", _exists(reports / "evaluation" / "baseline_test" / "metrics.json"), "reports/evaluation/baseline_test"),
        StatusItem("diagnóstico técnico", _exists(reports / "diagnostics.json"), "reports/diagnostics.json"),
        StatusItem("validação de aceite", _exists(reports / "acceptance_checks" / "acceptance_checks.md"), "reports/acceptance_checks"),
        StatusItem("auditoria técnica", _exists(reports / "project_audit" / "aps_audit.md"), "reports/project_audit/aps_audit.md"),
        StatusItem("relatório técnico consolidado", _exists(reports / "aps_report" / "relatorio_aps.md"), "reports/aps_report/relatorio_aps.md"),
        StatusItem("pacote técnico", _exists(reports / "delivery_pack" / "indice_entrega.md"), "reports/delivery_pack"),
        StatusItem("prontidão final escalável", "ok", "src/ecoscan/services/final_readiness.py; scripts/generate_final_readiness.py; aba Conclusão"),
        StatusItem("roadmap profissional", "ok", "docs/roadmap_profissional.md"),
        StatusItem("roteiro por etapas", "ok", "docs/roteiro_etapas_profissionalizacao.md"),
        StatusItem("exportação de evidência pela UI", "ok", "src/ecoscan/ui/streamlit_app.py"),
        StatusItem("design da interface", "ok", "src/ecoscan/ui/streamlit_app.py"),
        StatusItem("interface para dispositivo", "ok", "src/ecoscan/ui/streamlit_app.py e src/ecoscan/live_camera/server.py"),
        StatusItem("modelo final transfer learning", _exists(final_model), str(final_model)),
        StatusItem("detecção múltipla treinada", "future", "src/ecoscan/detection/contracts.py"),
    ]


def format_status_markdown(items: list[StatusItem]) -> str:
    lines = [
        "# Status técnico do EcoScan",
        "",
        "| Área | Status | Evidência |",
        "|---|---:|---|",
    ]
    for item in items:
        lines.append(f"| {item.area} | {item.status} | `{item.evidence}` |")
    lines.append("")
    lines.append("Status `pending` indica dependência de dataset final, dependência opcional ou treinamento futuro.")
    lines.append("Status `future` indica funcionalidade avançada fora do MVP inicial.")
    return "\n".join(lines)
