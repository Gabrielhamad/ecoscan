# Plano de execução em grande escala

Este plano organiza o EcoScan como projeto de APS, separando produto, dados, modelo, engenharia e apresentação.

## Norte técnico

O sistema deve continuar focado em uma imagem com um resíduo principal. A expansão para múltiplos objetos é evolução futura. O ganho de curto prazo vem de dataset melhor, curadoria e avaliação honesta.

## Frentes de trabalho

### 1. Dataset e sustentabilidade

Responsabilidade: definir classes, coletar imagens e revisar orientação ambiental.

Entregas:

- lote próprio de imagens por classe;
- manifesto de origem dos lotes;
- decisão sobre classes futuras;
- curadoria em `data/curated`;
- justificativa para resíduos especiais.

Gates:

- mínimo recomendado de 50 imagens úteis por classe para treinar versão final;
- nenhuma classe oficial sem orientação em `config/disposal_guidance.json`;
- nenhuma imagem de pessoa, documento, endereço ou dado sensível.

### 2. Processamento de imagens

Responsabilidade: demonstrar e justificar técnicas usadas no pipeline.

Entregas:

- comparação de filtros com imagens do dataset real;
- comparação de segmentação;
- análise dos elementos visuais segmentados;
- decisão documentada sobre filtro/segmentação padrão;
- evidências visuais em `reports/`.

Gates:

- explicar objetivo de cada filtro usado;
- documentar técnica que não ajudou;
- não aplicar segmentação como obrigação estética.

### 3. Modelo e avaliação

Responsabilidade: treinar, comparar e medir desempenho.

Entregas:

- baseline como referência;
- modelo final por transfer learning;
- métricas por classe;
- matriz de confusão;
- análise de erros.

Gates:

- treino, validação e teste separados;
- sem vazamento de imagens quase iguais;
- rejeição por baixa probabilidade ativa;
- modelo final comparado com baseline.

### 4. Produto e interface

Responsabilidade: deixar a apresentação simples e tecnicamente explicável.

Entregas:

- tela de análise;
- fluxo de câmera com captura e reconhecimento;
- modo de câmera ao vivo para celular com preferência por câmera traseira;
- overlay de tracking visual dos elementos segmentados;
- tela de processamento;
- tela de dataset;
- histórico local;
- logging técnico;
- tratamento de erros com código e ação recomendada;
- validação executável de aceite;
- status/auditoria da APS.

Gates:

- professor consegue testar uma imagem sem terminal;
- professor consegue capturar uma imagem pela câmera do navegador;
- professor consegue abrir o modo ao vivo e ver caixas/IDs sobre o resíduo;
- erros aparecem com código, mensagem clara e ação recomendada;
- detalhes técnicos estão visíveis sem poluir a tela principal;
- inferências reais ficam registradas em log técnico local.

### 5. Engenharia e qualidade

Responsabilidade: manter projeto executável e testável.

Entregas:

- testes automatizados;
- diagnóstico de ambiente;
- auditoria de requisitos;
- README atualizado;
- scripts reproduzíveis.

Gates:

- `python -m unittest discover -s tests` passando;
- `scripts/run_acceptance_checks.py` sem falhas;
- `scripts/project_audit.py` gerado antes da entrega;
- `scripts/project_status.py` atualizado;
- dependências instaladas no computador da apresentação.

## Ordem recomendada a partir de agora

1. Coletar lote próprio de imagens.
2. Fazer upload ou importação por pasta.
3. Rodar `scripts/analyze_dataset.py`.
4. Rodar `scripts/dataset_readiness.py`.
5. Revisar grades por classe em `reports/dataset_analysis`.
6. Criar e aplicar planilha de curadoria.
7. Recriar split a partir de `data/curated`.
8. Recalcular baseline.
9. Instalar TensorFlow em ambiente compatível.
10. Treinar MobileNetV2.
11. Avaliar e comparar.
12. Gerar relatório acadêmico consolidado.
13. Atualizar auditoria, status e relatório final.

## Decisões pendentes

- Quantas classes futuras entram na entrega final.
- Quantidade real de imagens por classe.
- Se `lamp`, `medicine`, `cooking_oil`, `aerosol` e `chemical_packaging` serão apenas discutidas ou também treinadas.
- Qual segmentação melhora o dataset real.
- Qual limiar de probabilidade será usado na versão final.
- Se a apresentação será feita apenas com Streamlit ou também com vídeo curto do fluxo.
- Se o modo ao vivo será apresentado por `localhost`, LAN com HTTPS/túnel ou gravação de demonstração.

## Risco principal

O risco mais alto é tentar aumentar o número de classes sem aumentar proporcionalmente o dataset. Para a APS, é melhor ter menos classes bem explicadas do que muitas classes com baixa evidência experimental.
