# Auditoria executável da APS — 07/11/2026

## Baseline e alcance

`main` remoto e clone conferidos: **89622ec714b815c216a9215ab9ba69999b39c6b8**.
Execução em 07/11/2026, America/Sao_Paulo; Python 3.12.14, Linux, ambiente virtual limpo,
instalado com `python -m pip install -e '.[dev]'`. Nenhuma alteração funcional.
Branch `audit/aps-baseline-2026-11-07`; autoria da execução: agente Codex a pedido do mantenedor.

Não foi localizado PDF do manual no workspace, incluindo os arquivos compartilhados.
A matriz usa `docs/plano_validacao_aps_4_dias.md` como referência secundária; não certifica
conformidade com o enunciado original. O plano relata manual com cabeçalho 2025/2:
confirmar a versão vigente antes do aceite acadêmico. Não há fotos reais de campo no clone.

O [inventário](evidencias_auditoria_aps/inventario.json) registra caminhos, SHA-256,
imports do pacote e nomes dos testes de todos os arquivos de `ui/`, `migrations/`,
`tests/` e dos módulos centrais pedidos. É inventário de superfície e cobertura,
não certificação de ausência de defeitos em todas as funcionalidades.
Os testes existentes não foram modificados. As sondas adicionais ficam apenas em `docs/`.

## Resultado executivo

Não foi reproduzida falha nos checks de regressão executados. A arquitetura implementa
PDI real e reconhecimento assistido. Há acoplamento reproduzido entre o filtro do
laboratório e a entrada do classificador; isso impede tratar todas as configurações
interativas como equivalentes à preparação validada. Não se demonstrou perda de acurácia
por esse acoplamento: faltam fotos novas, rótulos e avaliação independente.

O limiar do artefato é **0,8**, distinto de `confidence_threshold=0,65` na configuração
geral e do piso de ação de 0,72 usado na UI. Estes últimos não substituem o limiar ONNX
nem removem a confirmação. A configuração `confirmation_required=true` força
`accepted=False`, mesmo quando o classificador aceita uma hipótese.

Bloqueadores de aceite são evidências externas pendentes; não há base para declarar
o aplicativo quebrado nem para promover reconhecimento assertivo nesta auditoria.

## Arquitetura confirmada no código

| Camada | Responsabilidade e dependência real | Evidência executável |
| --- | --- | --- |
| Streamlit | `ui/streamlit_app.py` coordena identidade, recursos, navegação e controladores; `processing_configuration.py` converte seleção em opções; `analysis_controller.py` chama o serviço | `test_ui_modules.py`, `test_navigation_session_controllers.py`, `test_processing_lab.py` |
| Sessão e captura | `interaction_helpers.py` inclui foto, origem e opções na assinatura; alteração invalida análise. Temporário é removido pelo controlador | `test_streamlit_camera_flow.py`, `test_processing_lab.py`, `test_image_resource_limits.py` |
| Serviço | `analysis_service.py` executa pipeline, carrega bundle, prediz, compara contrato e aplica confirmação/escopo; segurança de apresentação em `recognition_safety.py` | `test_current_recognition.py`, `test_preserved_processing.py`, sonda adicional |
| PDI | EXIF/RGB → redução proporcional até 640 → filtro → segmentação e morfologia diagnósticas → RGB com margens 224×224 | `test_pipeline.py`, `test_preserved_processing.py`, `test_processing_evidence.py` |
| Encoder e cabeça | `semantic_onnx.py`: hashes de partes/encoder/cabeça, CPU ONNX, RGB uint8 → float32/255 → média/desvio CLIP → NCHW; combinação prior/cabeça e rejeição | `test_current_recognition.py`, smoke ONNX real |
| Treinamento | `semantic_learning.py`: contribuições aprovadas e consentidas, contrato do seed e encoder conferidos, mesmo pipeline padrão sem segmentação/morfologia, cabeça logística; avaliação histórica reutilizada | `test_semantic_learning.py` usa mocks de armazenamento/treino; não prova execução Supabase |
| Avaliação | `validate_semantic_onnx.py`: auditoria de manifesto/grupos/hashes, pipeline padrão sem máscaras, métricas do classificador antes da confirmação do produto | `test_evaluation_manifest.py`, `test_external_benchmark_evidence.py`; avaliação real de campo não executada |
| Dados | Supabase opcional; migrações 001 contribuições, 002 pontos/testes, 003 campanhas/relatos/auditoria, 004 identidade verificada | PostgreSQL 16 isolado: esquema, RLS, CAS, imutabilidade, auditoria e reaplicação 003/004 passaram |

As migrações revogam acesso de `anon`/`authenticated` às tabelas e concedem operações
ao `service_role`; RLS está habilitado. As constraints 004 são `NOT VALID`:
protegem novas escritas, mas não atestam saneamento de registros legados em produção.
Nenhum Supabase, banco de produção, segredo ou modelo remoto foi acessado/alterado.

## Reproduções e limites

Rodar `python docs/evidencias_auditoria_aps/reproduzir.py` na raiz, com as dependências
instaladas. [Código da sonda](evidencias_auditoria_aps/reproduzir.py) e
[saída completa](evidencias_auditoria_aps/reproducao.log) acompanham o PR.
Imagem sintética determinística e predição controlada servem exclusivamente para testar
contratos/políticas; não são evidência de campo ou desempenho do modelo.

1. **Inferência × novas contribuições de treino:** o RGB padrão foi idêntico pixel a
   pixel ao caminho `replace(default_processing_options(config), segmentation_name='none',
   morphology_name='none')` usado no treinamento e no avaliador. O contrato padrão
   coincide integralmente com `semantic.json` e `learning_seed.json`. O laboratório
   exporta o próprio array `recognition_image`, por identidade de objeto.
   **Não foi reproduzida divergência entre os caminhos padrão atuais.** Não é possível
   reconstruir a preparação das fotos que originaram os vetores históricos, ausentes do clone.
2. **Filtro do Streamlit → encoder:** AppTest executou o seletor público e seus reruns;
   a mesma conversão `selection.to_options()` alimentou o pipeline. Na cena sintética,
   mediana e gaussiano produziram hashes RGB e tensores diferentes de `none`.
   Sobel/Canny produziram o mesmo tensor de `none`: `pipeline.py` usa o RGB anterior
   aos filtros de borda. CLAHE/bilateral também alimentam `filter_result.image` por
   inspeção do ramo comum, mas não tiveram comparação de tensor nesta sonda.
   A captura de tensor usa `image_features` real com `session.run` substituído para
   observar a entrada normalizada, sem gerar scores neurais. O carregamento ONNX real
   foi verificado separadamente no smoke abaixo.
3. **Contrato do laboratório:** todas as seleções manuais sondadas (`none`, `median`,
   `gaussian`, `sobel`, `canny`) divergiram do contrato do artefato, que declara `auto`.
   Até Sobel/Canny, que preservam o RGB, recebem fingerprint distinto. O contrato descreve
   a seleção/configuração, não igualdade dos pixels. `analysis_service.py` compara o
   contrato **depois** de predizer e bloqueia aceitação em caso de diferença. Isso é
   comportamento conservador observado, não prova de modelo corrompido nem necessidade
   demonstrada de retreino para cada seleção.
4. **Confirmação:** com predição controlada `metal`, score 0,99, `accepted=True`,
   contrato padrão compatível e flag ligada, o serviço retorna `accepted=False`,
   `predicted_class=None`, mantendo `top_class=metal`. Desligada, retorna aceitação
   interna. Em ambos os casos o motor `semantic_onnx_assisted` continua em
   `needs_confirmation`, sem liberação de orientação pela política de segurança.
   A flag isolada não habilita comunicação assertiva. Nenhum gate foi contornado.
5. **Laboratório × normalização:** a visualização `preprocessing.normalized` é uma
   referência [0,1] da imagem de trabalho, não o tensor NCHW normalizado CLIP.
   `recognition_image` é o RGB efetivo antes da normalização CLIP. São representações
   diferentes documentadas; não foi reproduzida troca indevida entre elas.
6. **Histórico:** `evaluate_bundled_model.py` reproduziu 101/145 top-1, 51 aceitos,
   47 corretos, 4 incorretos e 94 rejeitados com limiar 0,8. O relatório declara
   `independent_test=false`; reutiliza vetores históricos. Sem métricas novas antes/depois,
   pois nenhum modelo foi alterado. [Relatório recalculado](evidencias_auditoria_aps/historico.json).

## Matriz APS → implementação → teste → observação → evidência

As referências T01–T15 vêm do plano secundário, não de inspeção direta do manual.
Todos os arquivos de teste abaixo integram a suíte executada com sucesso.

| Requisito APS | Código real | Teste | Falha observada / limite | Evidência |
| --- | --- | --- | --- | --- |
| T01 instalação e abertura | `pyproject.toml`, `ui/bootstrap.py` | `test_bootstrap`, `test_startup_stability` | Sem falha local; máquina da apresentação pendente | `dependencies.txt`, `pytest.log` |
| T02 contingência sem rede | runtime local e partes ONNX | `test_current_recognition`, smoke CPU | Smoke local passou; ensaio offline no dispositivo não executado | `onnx-smoke.log` |
| T03/T04 aquisição válida/inválida | `image_processing/image_io.py`, `validation.py` | `test_image_processing`, `test_image_resource_limits` | Sem falha automatizada; câmera física pendente | `pytest.log` |
| T05 filtros reais | `pipeline.py`, `image_processing/filters.py` | `test_adaptive_filters`, `test_gaussian_evidence`, sonda | Tensor varia com filtro; benefício em foto real não medido | `reproducao.log` |
| T06 segmentação | `segmentation/methods.py`, `adaptive.py` | `test_segmentation`, `test_adaptive_segmentation` | Sem falha automatizada; fotos reais/IoU não disponíveis | `laboratorio.log`, `pytest.log` |
| T07 morfologia | `segmentation/morphology.py` | `test_morphology`, `test_processing_lab` | Sem falha automatizada; experimento sintético não certifica cena real | `pytest.log` |
| T08 rastreabilidade PDI | `services/processing_evidence.py`, `ui/processing_lab.py` | `test_processing_evidence` | ZIP corresponde aos arrays; contém a própria foto quando real | `pytest.log`, sonda |
| T09 inferência segura | `semantic_onnx.py`, `analysis_service.py`, `recognition_safety.py` | `test_current_recognition`, `test_recognition_safety`, sonda | Confirmação é obrigatória; campo/calibração independente pendentes | `onnx-smoke.log`, `reproducao.log` |
| T10 descarte confirmado | `disposal/`, `ui/analysis_controller.py` | `test_guidance`, `test_disposal_targets`, `test_public_flow` | Sem falha nas regras; não mede acurácia visual | `pytest.log` |
| T11 navegação/perfis | `ui/session_state.py`, `navigation_controller.py`, identidade | `test_navigation_session_controllers`, `test_user_journeys`, `test_identity_ui` | Sem falha automatizada; isolamento no deploy pendente | `pytest.log`, `aceite.md` |
| T12 qualidade/banco | `.github/workflows/quality.yml`, `migrations/` | suíte completa, SQL de CI | Sem falha local; banco isolado não atesta Supabase real | `checks.json`, `postgresql.log` |
| T13 dispositivos reais | câmera/upload Streamlit | `test_streamlit_camera_flow`, `test_live_camera` | AppTest não substitui Android/iPhone físico | `aceite.md` QA-20 |
| T14 ensaios completos | fluxo público | `test_user_journeys` | Três ensaios cronometrados não executados | ausência declarada nesta auditoria |
| T15 documento/entrega | `docs/`, autoria e pacote APS | `test_academic_report`, `test_delivery_pack` | Testes estruturais não aprovam relatório, autoria ou postagem | `aceite.md`, plano de quatro dias |

Os nomes na coluna Teste omitem `.py` por legibilidade. Evidências estão em
[`docs/evidencias_auditoria_aps/`](evidencias_auditoria_aps/).

## Prioridades e estratégia proposta (sem implementar)

| Prioridade | Achado e natureza | Próxima ação e critério de fechamento |
| --- | --- | --- |
| P0 — aceite | Não há evidência de campo independente; QA-09 pendente. Bloqueia alegação assertiva, não a existência do app | Coletar fotos autorizadas, congelar hashes e grupos por objeto/sessão, auditar proveniência e comparar baseline/candidato no mesmo teste; precisão/recall/F1/rejeição por classe e calibração. Parar se fotos faltarem |
| P0 — entrega | Manual original, aceite no SHA publicado em aparelhos, ensaios e pacote final ausentes nesta execução | Conferir manual vigente; executar T01–T15 aplicáveis na máquina real e registrar SHA/responsável. Não inferir aceite a partir de CI |
| P1 — contrato | Filtros interativos alteram entrada e fingerprint; confirmação tem dois gates distintos. Reproduzido, sem regressão de acurácia demonstrada | Em etapa própria, decidir contrato estável de reconhecimento versus experimento PDI; testar tensor invariável caso se escolha isolamento, ou validar perfis suportados. Preservar abstenção e confirmação até aprovação por classe |
| P1 — avaliação | Por leitura, `validate_semantic_onnx.py` registra hash de preparação do modelo sem comparar contrato do pipeline; `semantic_learning.run` confere seed/config mas não reprocessa vetores históricos | Acrescentar em etapa própria guardas/testes para configuração alterada e origem dos vetores. Risco potencial de relatório inconsistente com configuração futura; não reproduzido como falha da baseline padrão |
| P1 — operação | QA-18/19/21 pendentes; SQL isolado não prova contas, persistência, backup ou dados legados | Validar em ambiente isolado autorizado e depois aceite do deploy, sem acesso à produção nesta etapa |
| P2 — reprodução | Dependências majoritariamente por intervalos; versões resolvidas registradas, sem falha nesta instalação | Avaliar lock/build reproduzível após compatibilidade com Streamlit Cloud; não trocar dependências na véspera sem regressão |
| P2 — diagnóstico | QA-11 usa marcadores estáticos e aponta atenção apesar dos testes de UI verdes | Revisar diagnóstico em etapa própria; não classificar atenção estática como quebra funcional |

## Cronograma até 11/11 (condicional às evidências)

| Data local | Trabalho proposto | Gate |
| --- | --- | --- |
| 07/11 | Revisar esta auditoria/PR, conferir manual, congelar baseline e iniciar coleta nova | CI verde + revisão; coleta não executada pelo agente |
| 08/11 | Avaliar fotos congeladas; PDI em pelo menos duas fotos reais; corrigir somente problemas reproduzidos em outra etapa | Relatórios com hashes, erros/rejeições e comparações, sem reutilizar treino como teste |
| 09/11 | Fixar candidato, testar PC/celulares e contas; revisar documentação APS | Aceite do mesmo SHA e segurança; repetir checks se código mudar |
| 10/11 | Três ensaios de 10–15 min, CI final, contingência testada, pacote e release revisados | GO/NO-GO rastreável; sem publicar/deploy por esta auditoria |
| 11/11 | Conferir entrega e apresentar versão congelada | Comprovante e acesso; nenhuma alegação de campo sem dados |

## Checks executados e reprodução

Resultados e tempos em [checks.json](evidencias_auditoria_aps/checks.json), versões em
[dependencies.txt](evidencias_auditoria_aps/dependencies.txt) e [ambiente.json](evidencias_auditoria_aps/ambiente.json).

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m ruff check src scripts tests
python -m pytest -q
python -m pip check
python docs/evidencias_auditoria_aps/reproduzir.py
python scripts/evaluate_bundled_model.py --output /tmp/ecoscan-historico.json
python scripts/run_acceptance_checks.py --diagnostic --output /tmp/ecoscan-aceite
python scripts/run_processing_lab.py --output /tmp/ecoscan-lab
```

- Ruff **passou**; pytest **496 passed, 108 subtests passed**; pip check **passou**.
- Sonda Streamlit/contratos **passou**; avaliação histórica **passou**, sem independência.
- Diagnóstico **passou no modo diagnóstico**: 9 OK, 4 atenção, 8 pendentes, 0 falhas.
  Não aprova release. QA-05/06/07 continuam pendentes por ausência de amostra real.
- Laboratório sintético **passou**. Não foi produzida evidência PDI de foto real.
- CPU ONNX real **passou** com imagem uniforme sintética 224×224; sete scores e limiar 0,8.
  Não mede acerto. O runtime avisou que o identificador de telemetria ficou em memória.
- PostgreSQL 16 isolado **passou**; sem conexão Supabase. Comandos SQL equivalentes ao job
  `community-database`: fixture, 001, 002, 003 duas vezes, 004 duas vezes, checks dentro
  de transação com rollback. Log inclui o resultado de cada etapa. Para repetir, executar na raiz
  `bash docs/evidencias_auditoria_aps/reproduzir_postgresql.sh` com Docker local disponível.
- [CI da baseline](https://github.com/Gabrielhamad/ecoscan/actions/runs/42387641972)
  **success** nos dois jobs de qualidade; snapshot em `baseline-ci.jsonl`.
  CI do PR deve ser conferida no SHA documental enviado, separadamente da baseline.

Para reproduzir o smoke ONNX, após instalar, executar:

```python
import numpy as np
from ecoscan.config import load_config
from ecoscan.services.analysis_service import load_model_bundle_for_analysis
bundle = load_model_bundle_for_analysis(load_config())
prediction = bundle.classifier.predict_image(np.full((224, 224, 3), 127, dtype=np.uint8))
assert len(prediction.probabilities) == 7 and prediction.threshold == 0.8
```

## Segurança, regressão e rollback

Mudanças restritas a este documento e evidências de auditoria em `docs/`.
Sem mudança de dependências declaradas, configuração, modelo versionado, aplicação ou SQL.
Não foram usados fotos privadas, contas reais ou credenciais de Supabase.
Logs e fixtures são locais/sintéticos; exportação de foto real permanece sujeita a autorização.
Risco funcional de regressão baixo por ausência de alteração executada pelo produto;
risco principal é interpretar probes/histórico/CI como validação de campo.
Rollback: reverter o commit documental deste PR, sem migração ou alteração de runtime.

**Próximo gate:** revisão do diagnóstico e CI do PR. Encerrar o Prompt 01 aqui;
nenhuma estratégia de correção acima está autorizada a avançar automaticamente para a próxima etapa.
