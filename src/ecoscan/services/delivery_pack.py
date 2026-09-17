from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from ecoscan.config import AppConfig
from ecoscan.services.aps_audit import build_aps_audit, summarize_audit
from ecoscan.services.completion import build_completion_plan, format_completion_markdown
from ecoscan.services.dataset_governance import build_dataset_readiness
from ecoscan.services.diagnostics import dataset_status, model_status


@dataclass(frozen=True)
class EvidenceItem:
    area: str
    path: str
    status: str
    purpose: str


@dataclass(frozen=True)
class AcceptanceCriterion:
    code: str
    scenario: str
    status: str
    evidence: str
    note: str


@dataclass(frozen=True)
class TechnicalDecision:
    code: str
    decision: str
    rationale: str
    status: str
    impact: str


@dataclass(frozen=True)
class DeliveryPack:
    generated_at_utc: str
    readiness_score: float
    raw_total: int
    curated_total: int
    selected_model: str
    evidence: tuple[EvidenceItem, ...]
    acceptance: tuple[AcceptanceCriterion, ...]
    decisions: tuple[TechnicalDecision, ...]


def _status_for_path(config: AppConfig, relative_path: str) -> str:
    path = config.project_root / relative_path
    return "ok" if path.exists() else "pending"


def _evidence(config: AppConfig) -> tuple[EvidenceItem, ...]:
    items = [
        EvidenceItem("execução", "README.md", "ok", "Instruções de instalação, execução e fluxo final."),
        EvidenceItem("manual APS", "docs/checklist_aps.md", "ok", "Checklist dos requisitos atendidos e pendentes."),
        EvidenceItem("arquitetura", "docs/arquitetura_final.md", "ok", "Separação das camadas do sistema."),
        EvidenceItem("roadmap", "docs/roadmap_profissional.md", "ok", "Marcos concluídos, riscos e evolução futura."),
        EvidenceItem("pipeline", "docs/pipeline_profissional_filtragem_reconhecimento.md", "ok", "Justificativa de filtro, segmentação e reconhecimento."),
        EvidenceItem("segmentação adaptativa", "docs/segmentacao_adaptativa.md", "ok", "Critérios de escolha automática da segmentação."),
        EvidenceItem("câmera ao vivo", "docs/live_camera_mobile.md", "ok", "Uso mobile com câmera traseira e tracking visual."),
        EvidenceItem("tratamento de erros", "docs/tratamento_erros.md", "ok", "Catálogo e contrato de erros do EcoScan."),
        EvidenceItem("UX dispositivo", "src/ecoscan/ui/streamlit_app.py", "ok", "Resumo executivo, barras de confiança e controles tocáveis."),
        EvidenceItem("interface", "src/ecoscan/ui/streamlit_app.py", "ok", "Aplicação Streamlit para demonstração principal."),
        EvidenceItem("modo ao vivo", "src/ecoscan/live_camera/server.py", "ok", "Servidor web local para reconhecimento de frames."),
        EvidenceItem("tracking", "src/ecoscan/live_camera/tracking.py", "ok", "Rastreamento por centroide dos componentes segmentados."),
        EvidenceItem("processamento", "src/ecoscan/app/pipeline.py", "ok", "Pipeline reproduzível de processamento de imagens."),
        EvidenceItem("filtros", "src/ecoscan/image_processing/filters.py", "ok", "Filtros acadêmicos parametrizáveis."),
        EvidenceItem("filtragem adaptativa", "src/ecoscan/image_processing/adaptive_filters.py", "ok", "Escolha automática de sequências de filtros por métricas de qualidade."),
        EvidenceItem("qualidade da captura", "src/ecoscan/image_processing/capture_quality.py", "ok", "Diagnóstico de captura com ações para melhorar a foto."),
        EvidenceItem("segmentação adaptativa", "src/ecoscan/segmentation/adaptive.py", "ok", "Escolha automática entre métodos conforme características da imagem."),
        EvidenceItem("métodos de segmentação", "src/ecoscan/segmentation/methods.py", "ok", "Otsu, HSV, GrabCut e controle sem segmentação."),
        EvidenceItem("elementos", "src/ecoscan/segmentation/elements.py", "ok", "Componentes conectados e overlay técnico."),
        EvidenceItem("orientações", "config/disposal_guidance.json", "ok", "Base separada de orientações ambientais."),
        EvidenceItem("destinos de descarte", "config/disposal_targets.json", "ok", "Cores, imagens, preparo e busca de pontos próximos."),
        EvidenceItem("impactos ambientais", "config/environmental_impacts.json", "ok", "Consequências do mau descarte, ação positiva e fontes de referência."),
        EvidenceItem("perfis", "config/user_profiles.json", "ok", "Perfis locais de usuário e administração para demonstração controlada."),
        EvidenceItem("contas e pontos", "src/ecoscan/services/accounts.py", "ok", "Persistência local de pontos por usuário e proteção contra pontuação duplicada."),
        EvidenceItem("campanha ambiental", "config/campaigns.json", "ok", "Missões, pontos, recompensas e responsabilidades da gestão ambiental."),
        EvidenceItem("missões e pontos", "src/ecoscan/services/campaigns.py", "ok", "Avaliação de missão com base no reconhecimento da imagem."),
        EvidenceItem("denúncias", "src/ecoscan/services/civic_reports.py", "ok", "Registro de denúncia com evidência, triagem visual, usuário solicitante e revisão administrativa."),
        EvidenceItem("pontos de coleta", "config/collection_points.json", "ok", "Base local de ecopontos filtrável por material e com links de rota."),
        EvidenceItem("orientação visual", "docs/orientacao_visual_e_pontos_coleta.md", "ok", "Fluxo usuário/gestão ambiental e pontos de coleta."),
        EvidenceItem("plano de fotos", "config/photo_requirements.json", "ok", "Lista de exemplos, variações e cuidados por classe do dataset."),
        EvidenceItem("histórico", "src/ecoscan/services/history.py", "ok", "Registro local opcional de inferências."),
        EvidenceItem("logs", "logs/ecoscan.log", _status_for_path(config, "logs/ecoscan.log"), "Registro técnico de inferências e falhas."),
        EvidenceItem("erros", "src/ecoscan/errors.py", "ok", "Contrato de erro com código, mensagem, ação recomendada e detalhe técnico controlado."),
        EvidenceItem("testes", "tests", "ok", "Testes automatizados do núcleo do projeto."),
        EvidenceItem("diagnóstico", "reports/diagnostics.json", _status_for_path(config, "reports/diagnostics.json"), "Estado de ambiente, dataset e modelo."),
        EvidenceItem("aceite executável", "reports/acceptance_checks/acceptance_checks.md", _status_for_path(config, "reports/acceptance_checks/acceptance_checks.md"), "Smoke test dos principais cenários da APS."),
        EvidenceItem("auditoria", "reports/project_audit/aps_audit.md", _status_for_path(config, "reports/project_audit/aps_audit.md"), "Gates de engenharia da APS."),
        EvidenceItem("relatório", "reports/aps_report/relatorio_aps.md", _status_for_path(config, "reports/aps_report/relatorio_aps.md"), "Relatório acadêmico consolidado."),
        EvidenceItem("filtros comparados", "reports/filter_experiments/metal_can/filter_comparison.jpg", _status_for_path(config, "reports/filter_experiments/metal_can/filter_comparison.jpg"), "Evidência visual de filtros."),
        EvidenceItem("segmentação comparada", "reports/segmentation_experiments/metal_can/segmentation_comparison.jpg", _status_for_path(config, "reports/segmentation_experiments/metal_can/segmentation_comparison.jpg"), "Evidência visual de segmentação."),
        EvidenceItem("matriz de confusão", "reports/evaluation/baseline_test/confusion_matrix.png", _status_for_path(config, "reports/evaluation/baseline_test/confusion_matrix.png"), "Avaliação da baseline."),
        EvidenceItem("modelo final", "models/ecoscan_transfer.keras", _status_for_path(config, "models/ecoscan_transfer.keras"), "Modelo final planejado por transfer learning."),
    ]
    return tuple(items)


def _acceptance(config: AppConfig) -> tuple[AcceptanceCriterion, ...]:
    final_model = model_status(config).final_model_exists
    summary, _ = build_dataset_readiness(config, target_per_class=50)
    return (
        AcceptanceCriterion(
            "AC-01",
            "Usuário envia imagem válida de resíduo.",
            "ok",
            "src/ecoscan/ui/streamlit_app.py; scripts/run_inference.py",
            "Fluxo de upload e inferência está implementado e testado.",
        ),
        AcceptanceCriterion(
            "AC-02",
            "Sistema aplica filtragem e segmentação antes do reconhecimento.",
            "ok",
            "src/ecoscan/app/pipeline.py; reports/processing_demo",
            "Pipeline registra sequência de filtros, parâmetros, máscara, qualidade da captura e entrada do modelo.",
        ),
        AcceptanceCriterion(
            "AC-03",
            "Usuário abre detalhes do processamento.",
            "ok",
            "Aba Processamento no Streamlit",
            "Mostra redimensionamento, filtro, máscara, segmentação, elementos e metadata.",
        ),
        AcceptanceCriterion(
            "AC-04",
            "Resultado traz classe, confiança e orientação de descarte.",
            "ok",
            "config/disposal_guidance.json; src/ecoscan/services/analysis_service.py",
            "Orientação fica fora do modelo e é recuperada pela classe prevista.",
        ),
        AcceptanceCriterion(
            "AC-05",
            "Imagem ruim ou fora do domínio não deve forçar resposta.",
            "ok",
            "models/baseline_classifier.json; tests/test_inference_service.py",
            "Há limiar de aceitação e mensagem de baixa segurança.",
        ),
        AcceptanceCriterion(
            "AC-06",
            "Arquivo inválido deve gerar erro claro.",
            "ok",
            "src/ecoscan/image_processing/validation.py; src/ecoscan/errors.py; tests/test_error_handling.py",
            "Validação cobre extensão, corrupção, arquivo vazio e tamanho mínimo; erros são padronizados.",
        ),
        AcceptanceCriterion(
            "AC-07",
            "Câmera do navegador captura e processa imagem.",
            "ok",
            "src/ecoscan/ui/streamlit_app.py",
            "Captura estática usa o mesmo pipeline de upload.",
        ),
        AcceptanceCriterion(
            "AC-08",
            "Câmera traseira do celular com reconhecimento ao vivo.",
            "ok",
            "src/ecoscan/live_camera; docs/live_camera_mobile.md",
            "Página mobile prioriza câmera traseira e faz tracking visual por segmentação.",
        ),
        AcceptanceCriterion(
            "AC-09",
            "Dataset final tem volume e curadoria adequados.",
            "attention" if not summary.ready_for_final_training else "ok",
            "reports/dataset_readiness/dataset_readiness.md; data/curated",
            "Dependente das fotos que o grupo ainda vai coletar.",
        ),
        AcceptanceCriterion(
            "AC-10",
            "Modelo final por transfer learning supera baseline.",
            "pending" if not final_model else "ok",
            "models/ecoscan_transfer.keras; reports/evaluation/transfer_test",
            "Fica para depois do dataset real e curado.",
        ),
        AcceptanceCriterion(
            "AC-11",
            "Interface em dispositivo deve ser clara e moderna.",
            "ok",
            "src/ecoscan/ui/streamlit_app.py; src/ecoscan/live_camera/server.py",
            "Resumo executivo, barras de confiança, painel live mobile e controles tocáveis foram implementados.",
        ),
        AcceptanceCriterion(
            "AC-12",
            "Resultado indica onde descartar e permite buscar ponto próximo.",
            "ok",
            "config/disposal_targets.json; assets/disposal_targets; src/ecoscan/disposal/targets.py",
            "Cada classe ativa possui cor, imagem de referência, preparo e consulta de mapa por localidade ou GPS.",
        ),
        AcceptanceCriterion(
            "AC-13",
            "Resultado explica consequências do descarte incorreto.",
            "ok",
            "config/environmental_impacts.json; src/ecoscan/disposal/impact.py",
            "Cada classe ativa possui riscos do mau descarte, ação positiva e fonte de referência.",
        ),
        AcceptanceCriterion(
            "AC-14",
            "Grupo sabe quais fotos coletar para fortalecer o reconhecimento.",
            "ok",
            "config/photo_requirements.json; aba Base de imagens",
            "Cada classe ativa possui exemplos de fotos, variações, restrições e meta mínima.",
        ),
        AcceptanceCriterion(
            "AC-15",
            "Usuário consulta pontos cadastrados compatíveis com o material.",
            "ok",
            "config/collection_points.json; aba Pontos de coleta",
            "Base local filtra por classe, exibe endereço, horário, materiais aceitos e rota no mapa.",
        ),
        AcceptanceCriterion(
            "AC-16",
            "Usuário participa de missões e acumula pontos.",
            "ok",
            "config/campaigns.json; src/ecoscan/services/campaigns.py; aba Campanha",
            "Missões rotativas usam tratamento de imagem e reconhecimento para validar evidências.",
        ),
        AcceptanceCriterion(
            "AC-17",
            "Usuário denuncia mau descarte com foto.",
            "ok",
            "src/ecoscan/services/civic_reports.py; aba Denúncia",
            "A denúncia registra evidência, qualidade da captura, filtro, segmentação, classe provável e status de triagem.",
        ),
        AcceptanceCriterion(
            "AC-18",
            "Participante acessa seus pontos e denúncias.",
            "ok",
            "config/user_profiles.json; src/ecoscan/services/accounts.py; aba Conta",
            "Pontuação e denúncias ficam vinculadas ao perfil ativo no protótipo local.",
        ),
        AcceptanceCriterion(
            "AC-19",
            "Admin revisa denúncias e acompanha participação.",
            "ok",
            "src/ecoscan/services/civic_reports.py; aba Gestão",
            "Perfil administrativo visualiza ranking, denúncias e registra decisão separada da triagem automática.",
        ),
    )


def _decisions() -> tuple[TechnicalDecision, ...]:
    return (
        TechnicalDecision(
            "DEC-01",
            "Manter Streamlit como interface principal.",
            "Reduz instalação, facilita apresentação e expõe etapas técnicas sem criar app desktop pesado.",
            "confirmada",
            "A APS consegue ser demonstrada localmente com baixo atrito.",
        ),
        TechnicalDecision(
            "DEC-02",
            "Adicionar página web separada para câmera ao vivo.",
            "Streamlit captura imagem estática; vídeo ao vivo exige controle direto de getUserMedia e canvas.",
            "confirmada",
            "Celular consegue priorizar câmera traseira e mostrar overlay em tempo quase real.",
        ),
        TechnicalDecision(
            "DEC-03",
            "Tratar tracking atual como segmentação geométrica, não YOLO.",
            "Sem dataset anotado por caixas, seria tecnicamente incorreto prometer detector multiobjeto treinado.",
            "confirmada",
            "Evita escopo inflado e mantém honestidade acadêmica.",
        ),
        TechnicalDecision(
            "DEC-04",
            "Congelar fortalecimento do reconhecimento até o dataset do grupo chegar.",
            "Métricas confiáveis dependem de dados reais, balanceados e curados.",
            "pendente de dados",
            "O projeto avança em entrega, documentação e qualidade sem mascarar limitação do modelo.",
        ),
        TechnicalDecision(
            "DEC-05",
            "Manter orientações de descarte em JSON configurável.",
            "O modelo deve classificar; regras ambientais precisam ser revisáveis pelo grupo.",
            "confirmada",
            "Facilita ajustes e evita acoplar recomendação ao classificador.",
        ),
        TechnicalDecision(
            "DEC-07",
            "Separar impactos ambientais das classes do modelo.",
            "Consequências do mau descarte e fontes de referência mudam com revisão de conteúdo, não com treinamento.",
            "confirmada",
            "Permite evolução institucional do app sem mexer no classificador.",
        ),
        TechnicalDecision(
            "DEC-08",
            "Criar base local de pontos de coleta revisável.",
            "Busca externa é útil, mas um uso institucional precisa de dados oficiais e editáveis.",
            "confirmada",
            "Secretaria, escola ou grupo pode cadastrar pontos por material sem alterar a visão computacional.",
        ),
        TechnicalDecision(
            "DEC-09",
            "Modelar campanha, missões e denúncias fora do classificador.",
            "A proposta pede atuação da Secretaria e participação do usuário; isso deve ser configurável e auditável, não embutido no modelo.",
            "confirmada",
            "A gestão ambiental pode ajustar missões, pontos, recompensas e triagem sem retreinar o reconhecimento.",
        ),
        TechnicalDecision(
            "DEC-10",
            "Usar perfis locais em vez de autenticação real nesta fase.",
            "O objetivo acadêmico é demonstrar papéis e fluxo de gestão sem armazenar senha de forma frágil em protótipo local.",
            "confirmada",
            "Usuário e admin ficam separados para demonstração; login seguro fica reservado para implantação web real.",
        ),
        TechnicalDecision(
            "DEC-06",
            "Usar MobileNetV2 como primeiro modelo final planejado.",
            "Boa relação entre explicabilidade, desempenho e execução local em projeto acadêmico.",
            "pendente de treino",
            "Só será promovido a modelo final após dataset curado e avaliação.",
        ),
    )


def build_delivery_pack(config: AppConfig) -> DeliveryPack:
    dataset = dataset_status(config)
    audit_summary = summarize_audit(build_aps_audit(config))
    selected_model = model_status(config)
    return DeliveryPack(
        generated_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        readiness_score=float(audit_summary["readiness_score"]),
        raw_total=sum(dataset.raw_counts.values()),
        curated_total=sum(dataset.curated_counts.values()),
        selected_model=selected_model.selected_kind,
        evidence=_evidence(config),
        acceptance=_acceptance(config),
        decisions=_decisions(),
    )


def write_delivery_pack(config: AppConfig, output_dir: str | Path | None = None) -> dict[str, Path]:
    report_dir = Path(output_dir).resolve() if output_dir else config.directories["reports"] / "delivery_pack"
    report_dir.mkdir(parents=True, exist_ok=True)
    pack = build_delivery_pack(config)

    paths = {
        "index": report_dir / "indice_entrega.md",
        "evidence": report_dir / "evidence_manifest.csv",
        "acceptance": report_dir / "criterios_aceite.csv",
        "completion": report_dir / "checklist_conclusao.md",
        "presentation": report_dir / "roteiro_apresentacao.md",
        "decisions": report_dir / "decisoes_tecnicas.md",
        "summary": report_dir / "delivery_pack.json",
    }

    paths["index"].write_text(_format_index(pack), encoding="utf-8")
    paths["completion"].write_text(
        format_completion_markdown(build_completion_plan(config)),
        encoding="utf-8",
    )
    paths["presentation"].write_text(_format_presentation_script(pack), encoding="utf-8")
    paths["decisions"].write_text(_format_decisions(pack.decisions), encoding="utf-8")
    _write_csv(paths["evidence"], pack.evidence)
    _write_csv(paths["acceptance"], pack.acceptance)
    paths["summary"].write_text(json.dumps(asdict(pack), indent=2, ensure_ascii=False), encoding="utf-8")
    return paths


def _format_index(pack: DeliveryPack) -> str:
    ok_acceptance = sum(1 for item in pack.acceptance if item.status == "ok")
    lines = [
        "# Pacote de entrega APS - EcoScan",
        "",
        f"Gerado em UTC: `{pack.generated_at_utc}`.",
        "",
        "## Resumo executivo",
        "",
        f"- Score de prontidão da auditoria: {pack.readiness_score}%.",
        f"- Dataset bruto atual: {pack.raw_total} imagens.",
        f"- Dataset curado atual: {pack.curated_total} imagens.",
        f"- Modelo selecionado em execução: `{pack.selected_model}`.",
        f"- Critérios de aceite em `ok`: {ok_acceptance}/{len(pack.acceptance)}.",
        "",
        "## Leitura correta para apresentação",
        "",
        "O EcoScan já demonstra aquisição, validação, filtragem, segmentação, classificação, orientação, histórico, câmera, tratamento de erros e evidências. "
        "O reconhecimento definitivo fica condicionado ao dataset real do grupo e ao treino final por transfer learning.",
        "",
        "## Arquivos gerados",
        "",
        "- `evidence_manifest.csv`: inventário de evidências.",
        "- `criterios_aceite.csv`: matriz dos cenários da APS.",
        "- `checklist_conclusao.md`: leitura final do que está pronto e do que depende de dados/modelo.",
        "- `roteiro_apresentacao.md`: fala sugerida para apresentação.",
        "- `decisoes_tecnicas.md`: decisões e pendências controladas.",
        "- `delivery_pack.json`: resumo estruturado para auditoria.",
        "",
        "## Próxima ação recomendada",
        "",
        "Ensaiar a apresentação com uma imagem boa, uma imagem ruim, uma captura de câmera e a aba de processamento aberta.",
        "",
    ]
    return "\n".join(lines)


def _format_presentation_script(pack: DeliveryPack) -> str:
    return "\n".join(
        [
            "# Roteiro de apresentação - EcoScan",
            "",
            "## 1. Abertura",
            "",
            "Apresentar o problema: descarte incorreto de recicláveis, orgânicos, pilhas, baterias e eletrônicos.",
            "",
            "## 2. Objetivo",
            "",
            "Explicar que o sistema recebe imagem de um resíduo principal, processa a imagem, classifica a categoria e orienta o descarte.",
            "",
            "## 3. Demonstração do usuário",
            "",
            "Abrir o Streamlit, enviar uma imagem e mostrar classe, score, categoria ambiental e orientação.",
            "",
            "## 4. Demonstração técnica",
            "",
            "Abrir a aba `Processamento` e mostrar original, redimensionamento, filtro, segmentação, entrada do modelo, elementos detectados e metadata.",
            "",
            "## 5. Câmera",
            "",
            "Mostrar a captura por navegador e, se o ambiente permitir, abrir o `EcoScan Live` no celular para câmera traseira e tracking visual.",
            "",
            "## 6. Campanha e denúncias",
            "",
            "Mostrar a aba `Campanha`, explicar missões rotativas, pontos e recompensas. Depois abrir `Denúncia` e mostrar que a evidência passa por tratamento, segmentação, reconhecimento e triagem.",
            "",
            "## 7. Avaliação",
            "",
            "Mostrar que há baseline, matriz de confusão, métricas além de accuracy e rejeição de predições incertas.",
            "",
            "## 8. Tratamento de erros",
            "",
            "Mostrar que entradas inválidas, modelo ausente, dependências opcionais e falhas de câmera retornam código, mensagem e ação recomendada.",
            "",
            "## 8. Limitações honestas",
            "",
            "Deixar claro que o dataset final e o modelo por transfer learning entram depois das imagens do grupo.",
            "",
            "## 9. Fechamento",
            "",
            f"Concluir com o score de prontidão atual ({pack.readiness_score}%) e os próximos passos: coletar, curar, treinar e reavaliar.",
            "",
        ]
    )


def _format_decisions(decisions: Iterable[TechnicalDecision]) -> str:
    lines = [
        "# Decisões técnicas do EcoScan",
        "",
        "| Código | Decisão | Justificativa | Status | Impacto |",
        "|---|---|---|---:|---|",
    ]
    for item in decisions:
        lines.append(
            f"| {item.code} | {item.decision} | {item.rationale} | {item.status} | {item.impact} |"
        )
    lines.append("")
    return "\n".join(lines)


def _write_csv(path: Path, rows: Iterable[object]) -> None:
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(asdict(rows[0]).keys())
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
