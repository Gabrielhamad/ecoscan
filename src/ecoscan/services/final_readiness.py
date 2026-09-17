from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from ecoscan.config import AppConfig
from ecoscan.services.completion import build_completion_plan


@dataclass(frozen=True)
class FinalReadinessItem:
    area: str
    title: str
    status: str
    prepared_for_later: bool
    evidence: str
    next_step: str


def build_final_readiness_items(config: AppConfig) -> tuple[FinalReadinessItem, ...]:
    plan = build_completion_plan(config)
    project_root = Path(config.project_root)
    feedback_manifest = config.directories["reports"] / "recognition_feedback" / "feedback.csv"
    upload_manifest = config.directories["reports"] / "dataset_uploads" / "upload_manifest.csv"

    return (
        FinalReadinessItem(
            area="Produto",
            title="Experiência cidadão e secretaria separada por perfil",
            status="ready" if plan.ready_for_demo else "attention",
            prepared_for_later=True,
            evidence="src/ecoscan/ui/streamlit_app.py; config/user_profiles.json",
            next_step="Trocar perfis locais por autenticação quando sair do protótipo.",
        ),
        FinalReadinessItem(
            area="Operação",
            title="Campanhas, missões, pontos e denúncias integrados",
            status="ready",
            prepared_for_later=True,
            evidence="config/campaigns.json; config/collection_points.json; reports/civic_reports",
            next_step="Validar regras e pontos oficiais antes de uso institucional real.",
        ),
        FinalReadinessItem(
            area="Dados",
            title="Entrada de novas imagens e correções do reconhecimento",
            status="ready" if feedback_manifest.exists() or upload_manifest.exists() else "prepared",
            prepared_for_later=True,
            evidence="reports/recognition_feedback; reports/dataset_uploads; src/ecoscan/services/dataset_ingestion.py",
            next_step="Usar correções reais do grupo para alimentar curadoria e novo treino.",
        ),
        FinalReadinessItem(
            area="Dados",
            title="Base curada pronta para treino final",
            status="ready" if plan.ready_for_final_training else "needs_data",
            prepared_for_later=True,
            evidence="data/curated; reports/dataset_readiness",
            next_step="Completar curadoria por classe, evitando duplicatas, rótulos errados e imagens irreais.",
        ),
        FinalReadinessItem(
            area="Modelo",
            title="Promoção controlada do modelo final",
            status="ready" if plan.final_model_exists else "needs_training",
            prepared_for_later=True,
            evidence="src/ecoscan/services/model_governance.py; " + plan.selected_model_kind,
            next_step="Treinar, avaliar em validação/teste, passar nos casos difíceis e promover somente se superar o modelo atual.",
        ),
        FinalReadinessItem(
            area="Qualidade",
            title="Validação executável antes da entrega",
            status="ready" if plan.acceptance_failed == 0 and plan.acceptance_ok > 0 else "attention",
            prepared_for_later=True,
            evidence="reports/acceptance_checks; scripts/run_acceptance_checks.py",
            next_step="Rodar aceite após cada mudança relevante e anexar relatório atualizado.",
        ),
        FinalReadinessItem(
            area="Implantação",
            title="Publicação gratuita HTTPS para testes do grupo",
            status="prepared",
            prepared_for_later=True,
            evidence="streamlit_app.py; docs/hospedagem_gratuita.md; src/ecoscan/services/deployment_readiness.py",
            next_step="Configurar login, publicar e validar acesso e persistência na URL HTTPS antes de compartilhar.",
        ),
        FinalReadinessItem(
            area="Implantação",
            title="Produção institucional com câmera ao vivo dedicada",
            status="future",
            prepared_for_later=False,
            evidence=".env.example; Dockerfile; docs/acesso_multidispositivo.md",
            next_step="Publicar backend principal e EcoScan Live em HTTPS, com persistência e autenticação reais.",
        ),
        FinalReadinessItem(
            area="Segurança",
            title="Autenticação, papéis reais e proteção de evidências",
            status="prepared",
            prepared_for_later=True,
            evidence="src/ecoscan/services/identity.py; docs/autenticacao.md",
            next_step="Configurar OIDC e validar login real. Concluir persistência e política de retenção de imagens.",
        ),
        FinalReadinessItem(
            area="Visão computacional",
            title="Detecção múltipla treinada por objeto",
            status="future",
            prepared_for_later=True,
            evidence=str(project_root / "src" / "ecoscan" / "detection"),
            next_step="Após dataset rotulado por objeto, treinar detector e ligar ao contrato já reservado.",
        ),
    )


def summarize_final_readiness(items: tuple[FinalReadinessItem, ...]) -> dict[str, int]:
    return dict(Counter(item.status for item in items))


def format_final_readiness_markdown(items: tuple[FinalReadinessItem, ...]) -> str:
    lines = [
        "# Estrutura final e escalável - EcoScan",
        "",
        "| Área | Item | Status | Preparado para depois | Evidência | Próximo passo |",
        "|---|---|---:|---:|---|---|",
    ]
    for item in items:
        prepared = "sim" if item.prepared_for_later else "parcial"
        lines.append(
            "| "
            f"{item.area} | {item.title} | {item.status} | {prepared} | "
            f"`{item.evidence}` | {item.next_step} |"
        )
    lines.append("")
    return "\n".join(lines)
