from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ecoscan.config import AppConfig
from ecoscan.services.diagnostics import dataset_status, model_status


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _percent(value: Any) -> str:
    if not isinstance(value, int | float):
        return "indisponível"
    return f"{value * 100:.1f}%"


def _dataset_table(config: AppConfig) -> list[str]:
    status = dataset_status(config)
    lines = [
        "| Classe | Raw | Curated | Train | Validation | Test |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for class_id in config.classes:
        lines.append(
            "| "
            f"{class_id} | {status.raw_counts[class_id]} | {status.curated_counts[class_id]} | "
            f"{status.train_counts[class_id]} | {status.validation_counts[class_id]} | {status.test_counts[class_id]} |"
        )
    return lines


def _dependency_summary(config: AppConfig) -> str:
    diagnostics = _load_json(config.directories["reports"] / "diagnostics.json")
    dependencies = diagnostics.get("dependencies", [])
    if not dependencies:
        return "Diagnóstico de dependências ainda não gerado."
    missing = [item["name"] for item in dependencies if not item.get("installed")]
    if not missing:
        return "Todas as dependências verificadas estavam disponíveis no ambiente local."
    return "Dependências opcionais ausentes no ambiente atual: " + ", ".join(missing) + "."


def _baseline_summary(config: AppConfig) -> list[str]:
    metrics = _load_json(config.directories["reports"] / "evaluation" / "baseline_test" / "metrics.json")
    if not metrics:
        return ["Métricas da baseline ainda não foram geradas."]
    return [
        f"- Accuracy com rejeição: {_percent(metrics.get('accuracy'))}.",
        f"- Macro precision: {_percent(metrics.get('macro_precision'))}.",
        f"- Macro recall: {_percent(metrics.get('macro_recall'))}.",
        f"- Macro F1-score: {_percent(metrics.get('macro_f1'))}.",
        f"- Predições incertas: {metrics.get('uncertain_count', 'indisponível')}/{metrics.get('total', 'indisponível')}.",
    ]


def _readiness_summary(config: AppConfig) -> list[str]:
    readiness = _load_json(config.directories["reports"] / "dataset_readiness" / "dataset_readiness.json")
    summary = readiness.get("summary", {})
    if not summary:
        return ["Relatório de prontidão do dataset ainda não foi gerado."]
    return [
        f"- Alvo por classe: {summary.get('target_per_class')}.",
        f"- Total bruto: {summary.get('raw_total')}.",
        f"- Total curado: {summary.get('curated_total')}.",
        f"- Classes no alvo bruto: {summary.get('classes_at_raw_target')}/{summary.get('class_count')}.",
        f"- Imagens brutas ainda necessárias: {summary.get('missing_raw_total')}.",
        f"- Pronto para treinamento final: {summary.get('ready_for_final_training')}.",
    ]


def _audit_attention(config: AppConfig) -> list[str]:
    audit = _load_json(config.directories["reports"] / "project_audit" / "aps_audit.json")
    items = audit.get("items", [])
    attention = [
        item for item in items
        if item.get("priority") == "alta" and item.get("status") in {"attention", "pending"}
    ]
    if not attention:
        return ["Nenhuma atenção alta registrada na auditoria atual."]
    return [
        f"- {item.get('code')}: {item.get('rationale')} Próxima ação: {item.get('next_action')}"
        for item in attention
    ]


def build_academic_report(config: AppConfig) -> str:
    dataset = dataset_status(config)
    selected_model = model_status(config)
    raw_total = sum(dataset.raw_counts.values())
    curated_total = sum(dataset.curated_counts.values())
    split_total = sum(dataset.train_counts.values()) + sum(dataset.validation_counts.values()) + sum(dataset.test_counts.values())
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    lines = [
        "# EcoScan: Guia Inteligente de Descarte de Resíduos",
        "",
        f"Relatório técnico gerado em {generated_at}.",
        "",
        "## 1. Problema",
        "",
        "Pessoas comuns frequentemente têm dúvidas sobre o descarte correto de resíduos. "
        "Isso pode causar descarte inadequado de recicláveis, orgânicos, pilhas, baterias e eletrônicos.",
        "",
        "## 2. Objetivo",
        "",
        "Desenvolver uma aplicação local de visão computacional que receba uma imagem com um resíduo principal, "
        "aplique processamento digital de imagens, classifique a categoria visual e retorne uma orientação de descarte configurável.",
        "",
        "## 3. Escopo",
        "",
        "O MVP trabalha com classificação de uma imagem contendo um resíduo principal. "
        "O modo ao vivo rastreia componentes segmentados, mas detecção supervisionada de múltiplas classes por objeto "
        "está documentada como evolução futura, fora do núcleo atual.",
        "",
        "Classes ativas: " + ", ".join(f"`{class_id}`" for class_id in config.classes) + ".",
        "",
        "## 4. Arquitetura",
        "",
        "O projeto separa interface, aquisição, validação, pré-processamento, filtros, segmentação, classificação, "
        "orientações de descarte, histórico, diagnósticos e relatórios. Essa separação reduz acoplamento e facilita explicar a solução.",
        "",
        "## 5. Aquisição e validação",
        "",
        "A interface permite upload e captura por câmera pelo navegador. O projeto também possui um modo ao vivo para celular, "
        "com preferência pela câmera traseira e envio periódico de frames ao backend local. Após capturar uma foto ou receber um frame, "
        "o mesmo pipeline executa filtro, segmentação, análise de elementos visuais e reconhecimento. O pipeline valida extensão, "
        "existência do arquivo, arquivo vazio, corrupção e tamanho mínimo antes de qualquer inferência.",
        "",
        "## 6. Dataset",
        "",
        f"Estado atual: {raw_total} imagens brutas, {curated_total} imagens curadas e {split_total} imagens em treino/validação/teste.",
        "",
        *_dataset_table(config),
        "",
        "### Prontidão do dataset",
        "",
        *_readiness_summary(config),
        "",
        "## 7. Processamento digital de imagens",
        "",
        "O pipeline é parametrizável e inclui redimensionamento, normalização, filtragem adaptativa, filtros manuais e preparação da entrada do modelo. "
        "O modo automático avalia brilho, contraste, saturação, nitidez e densidade de bordas antes de comparar sequências curtas de preparação. "
        "Os filtros disponíveis para demonstração incluem Gaussiano, mediana, CLAHE, Sobel, Canny e bilateral quando OpenCV estiver instalado.",
        "",
        "## 8. Segmentação",
        "",
        "A segmentação foi implementada de forma modular. Otsu pode ser demonstrado sem OpenCV; HSV e GrabCut ficam disponíveis com OpenCV. "
        "Após a segmentação, o sistema analisa componentes conectados para estimar elementos visuais significativos, área relativa e caixas delimitadoras. "
        "No modo ao vivo, essas caixas alimentam um tracking simples por centroide para manter IDs estáveis entre frames. "
        "A decisão final sobre usar segmentação como padrão deve ser baseada no dataset real do grupo.",
        "",
        "## 9. Modelagem",
        "",
        f"Modelo selecionado atualmente: `{selected_model.selected_kind}`.",
        f"Caminho selecionado: `{selected_model.selected_path}`.",
        "",
        "A baseline atual usa características simples e KNN. O modelo final planejado é transfer learning com MobileNetV2, "
        "dependente de dataset curado e TensorFlow disponível.",
        "",
        "## 10. Avaliação",
        "",
        *_baseline_summary(config),
        "",
        "A baseline deve ser apresentada como referência acadêmica, não como desempenho final. "
        "A baixa métrica atual reforça a necessidade de dataset próprio, curadoria e transfer learning.",
        "",
        "## 11. Tratamento de incerteza",
        "",
        "O sistema usa limiar de probabilidade para evitar forçar respostas. Quando o score é baixo, a interface informa que não foi possível "
        "identificar o resíduo com segurança e sugere melhorar iluminação, fundo e enquadramento.",
        "",
        "## 12. Tratamento de erros",
        "",
        "O EcoScan possui contrato centralizado de erros em `src/ecoscan/errors.py`. "
        "Falhas conhecidas são apresentadas com código, título, mensagem amigável, ação recomendada e categoria. "
        "A interface e o modo ao vivo evitam expor stack trace bruto ao usuário, enquanto os detalhes técnicos ficam disponíveis para log e diagnóstico.",
        "",
        "## 13. Orientação de descarte",
        "",
        "As orientações ficam em `config/disposal_guidance.json`, separadas do modelo. O modelo classifica; outro módulo transforma a classe em orientação.",
        "",
        "A versão atual também usa `config/disposal_targets.json` e `config/environmental_impacts.json` para apresentar cor ou ponto de descarte, preparo do material, busca de ponto próximo e consequências do descarte incorreto.",
        "",
        "## 14. Campanha, missões e denúncia",
        "",
        "Com base na proposta de atuação da Secretaria do Ambiente, a versão atual inclui `config/campaigns.json` com campanha pública, missões rotativas, pontuação e recompensas simbólicas. `config/user_profiles.json` separa perfil de usuário e perfil administrativo para demonstrar o fluxo institucional sem misturar papéis.",
        "",
        "A aba `Campanha` valida evidências por imagem usando o mesmo pipeline de tratamento, segmentação e reconhecimento. Os pontos são registrados em `reports/accounts/points_ledger.csv`, vinculados ao perfil ativo e protegidos contra pontuação duplicada da mesma comprovação.",
        "",
        "A aba `Denúncia` registra evidência de mau descarte em manifesto local, salvando qualidade da captura, filtro, segmentação, classe provável e status de triagem. A aba `Gestão`, disponível para o perfil administrativo, registra decisão humana separada da triagem automática. Essa verificação deve ser tratada como apoio técnico para revisão, não como prova definitiva sem vistoria humana.",
        "",
        "## 15. Testes e reprodutibilidade",
        "",
        "O projeto contém testes automatizados com `unittest`, scripts de diagnóstico, análise de dataset, split, baseline, avaliação, "
        "validação executável de aceite, auditoria, prontidão do dataset e pacote de entrega APS com evidências e critérios de aceite.",
        "",
        "## 16. Limitações atuais",
        "",
        *_audit_attention(config),
        "",
        "## 17. Ambiente",
        "",
        _dependency_summary(config),
        "",
        "## 18. Conclusão",
        "",
        "O EcoScan já possui estrutura técnica sólida para a APS: aquisição, validação, processamento, segmentação, baseline, "
        "câmera ao vivo, tracking visual, tratamento de erros, orientação de descarte, perfis, campanha, missões, denúncia, gestão, histórico, interface e relatórios. A evolução crítica agora é de dados: coletar imagens próprias, "
        "curar o dataset e treinar o modelo final.",
        "",
    ]
    return "\n".join(lines)


def write_academic_report(config: AppConfig, output_path: str | Path | None = None) -> Path:
    path = Path(output_path).resolve() if output_path else config.directories["reports"] / "aps_report" / "relatorio_aps.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_academic_report(config), encoding="utf-8")
    return path
