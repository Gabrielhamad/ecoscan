# Aceite final da APS — revisão adversarial

**Veredito: NO-GO para congelar/publicar a entrega final.** O app e o ONNX abrem
localmente, os testes existentes passam e o reconhecedor ativo exige confirmação.
Isso não elimina os defeitos de continuidade/privacidade reproduzidos, integra os
PRs nem supre as fotos reais, os dispositivos e os ensaios ausentes.

**Fonte examinada:** `main` **89622ec714b815c216a9215ab9ba69999b39c6b8**,
reconfirmada no GitHub. Não existe candidata integrada diferente dessa baseline.
A execução ocorreu em **09/11/2026 UTC**, iniciada na noite de
**08/11/2026 em America/Sao_Paulo**; a coleta documental se estendeu à madrugada
de 09/11 local. Horários exatos constam nos JSONs. O título
do Prompt 12 prevê 10/11, mas não é a data de um ensaio realizado.
O SHA do PR desta auditoria identifica o documento, não uma release aprovada.

Foi adotada a postura de QA adversarial, com sondas independentes da suíte já
existente. Não houve segundo auditor humano nem avaliação de campo independente.
Este PR acrescenta somente documentação, sondas e evidências sanitizadas em
`docs/`; não corrige o runtime, altera pesos, configuração, autenticação, banco
ou deployment. Nenhuma conta real ou dado Supabase foi acessado.

## Base normativa, alcance e cadeia de evidências

O grupo confirmou que não há URL institucional disponível para o manual/ficha.
Usa-se o [resumo versionado][plano], com a ressalva já aceita: o nome recebido
contém 2026, mas o cabeçalho descrito é 2025/2; o PDF e o modelo oficial não estão
no workspace. Não se atesta conformidade integral com a edição oficial 2026.
T01–T15 são critérios sugeridos pelo projeto, não numeração oficial do manual.
O resumo exige programa e apresentação; não há exigência demonstrada de `.exe`.

| Evidência versionada neste PR | Conteúdo verificável |
| --- | --- |
| [checks.json](evidencias_aceite_final/checks.json) | Comandos, versões efetivamente resolvidas, saídas resumidas, retornos e não executados |
| [probes.json](evidencias_aceite_final/probes.json) / [reproduzir.py](evidencias_aceite_final/reproduzir.py) | 32 casos técnicos: **21 PASS, 5 FAIL, 6 BLOCKED**; fixtures artificiais identificadas, sem métrica de campo |
| [browser.json](evidencias_aceite_final/browser.json) / [smoke_browser.py](evidencias_aceite_final/smoke_browser.py) | Chromium Linux local: **9 PASS, 2 FAIL**; nenhuma conta real ou telefone |
| [pdi_summary.json](evidencias_aceite_final/pdi_summary.json) | Exportador oficial, parâmetros, diferenças, hashes, tempos e lista dos 23 arquivos locais |
| [historical.json](evidencias_aceite_final/historical.json) | Reexecução de vetores históricos: `independent_test=false` |
| [acceptance_summary.json](evidencias_aceite_final/acceptance_summary.json) | Aceite estrito incompleto, retorno **2**; QA-09/18/19/20/21 pendentes |
| [pr_review.json](evidencias_aceite_final/pr_review.json) | Heads completos, descrições/diffs identificados por hash, arquivos e CI dos 11 PRs do ciclo |
| [integration.json](evidencias_aceite_final/integration.json) | Comparação de artefatos e merges virtuais entre pares, sem integrar branches |
| [ci_snapshot.json](evidencias_aceite_final/ci_snapshot.json) | Workflow de qualidade correto e distinção do treinamento agendado |
| [README de reprodução](evidencias_aceite_final/README.md) | Isolamento local, comandos e limites das sondas |

`PASS` vale somente para o escopo descrito. `FAIL` exige reprodução registrada.
`BLOCKED` indica evidência/equipamento ausente, não defeito presumido. Os hashes
do [manifesto documental](evidencias_aceite_final/manifest.json) permitem conferir
as evidências; não certificam origem independente das fotos nem aceite humano.

## PRs do ciclo versus o main

Foram obtidos os metadados, as descrições e os diffs unificados de **#20–#30**;
trechos críticos foram confrontados com o código e as reproduções no main.
Não se executou uma combinação hipotética de todos os PRs. Todos partem de
`89622ec...`, continuam **não integrados** e possuem CI verde em seus próprios
heads. A lista completa dos SHAs está no JSON, além dos links abaixo.

| PR / etapa | Conclusão da revisão | CI do head observado |
| --- | --- | --- |
| [#20](https://github.com/Gabrielhamad/ecoscan/pull/20), auditoria | Acoplamento PDI/inferência e confirmação novamente reproduzidos; diagnóstico não resolve defeitos | [42413153906](https://github.com/Gabrielhamad/ecoscan/actions/runs/42413153906) |
| [#21](https://github.com/Gabrielhamad/ecoscan/pull/21), trilhas | Propõe separar RGB oficial e laboratório; a invariância ainda falha em main | [42414126562](https://github.com/Gabrielhamad/ecoscan/actions/runs/42414126562) |
| [#22](https://github.com/Gabrielhamad/ecoscan/pull/22), campo | Ferramentas de manifesto/grupos/direitos; não fornecem o corpus real ausente | [42415626661](https://github.com/Gabrielhamad/ecoscan/actions/runs/42415626661) |
| [#23](https://github.com/Gabrielhamad/ecoscan/pull/23), candidatos | Experimentos offline sem promoção de pesos; nenhum ganho novo demonstrado | [42417696695](https://github.com/Gabrielhamad/ecoscan/actions/runs/42417696695) |
| [#24](https://github.com/Gabrielhamad/ecoscan/pull/24), decisão | Seis estados/política por classe; todos os opt-ins assertivos estão desativados | [42495344781](https://github.com/Gabrielhamad/ecoscan/actions/runs/42495344781) |
| [#25](https://github.com/Gabrielhamad/ecoscan/pull/25), PDI | Relatórios e métricas condicionadas a referência; faltam fotos reais autorizadas | [42506398848](https://github.com/Gabrielhamad/ecoscan/actions/runs/42506398848) |
| [#26](https://github.com/Gabrielhamad/ecoscan/pull/26), UX | Contém correção manual após falha e sanitização do boundary; ainda não protegem main | [42509633715](https://github.com/Gabrielhamad/ecoscan/actions/runs/42509633715) |
| [#27](https://github.com/Gabrielhamad/ecoscan/pull/27), qualidade | Locks/gates adicionais não fazem parte da CI atual de main; verificar conjunto integrado | [42511547792](https://github.com/Gabrielhamad/ecoscan/actions/runs/42511547792) |
| [#28](https://github.com/Gabrielhamad/ecoscan/pull/28), deploy | Registro anterior: 3 PASS técnicos, 1 falha local, 27 `manual_pending`; não aprova site/contas | [42518505960](https://github.com/Gabrielhamad/ecoscan/actions/runs/42518505960) |
| [#29](https://github.com/Gabrielhamad/ecoscan/pull/29), execução | ZIP de revisão e launcher; `release_ready=false`; correção de cache frio não integrada | [42522161332](https://github.com/Gabrielhamad/ecoscan/actions/runs/42522161332) |
| [#30](https://github.com/Gabrielhamad/ecoscan/pull/30), acadêmico | Markdown/DOCX, índice e seminário para revisão; dependem de evidências reais e atualização após integração | [42549834707](https://github.com/Gabrielhamad/ecoscan/actions/runs/42549834707) |

**Errata de rastreabilidade:** o corpo do PR #29 e os materiais do PR #30
referenciam `42513163053` como qualidade da baseline. A API mostra que esse run
é **Treinamento revisado**, com um job `train`. A evidência correta de qualidade
do mesmo SHA é [42387641972][ci-main], com os jobs de testes e PostgreSQL 16
concluídos com sucesso. Não é uma falha dessa CI; é um erro documental **P2**.
Corrigir a referência e regenerar DOCX/manifestos afetados antes de distribuí-los.

Merges virtuais por `git merge-tree` reproduziram conflitos de conteúdo:

| Par de PRs | Arquivos em conflito |
| --- | --- |
| #21 + #24 | `services/analysis_service.py` |
| #21 + #25 | `docs/pratica_processamento_imagens.md`, `ui/processing_lab.py` |
| #24 + #26 | `services/analysis_service.py`, `public_flow.py`, `recognition_safety.py`, `ui/analysis_controller.py`, `common_views.py` |
| #29 + #30 | `scripts/README.md` |
| #27 + #29; #27 + #30 | Nenhum conflito textual nesses pares; compatibilidade funcional conjunta não testada |

Logo, CI verde em cada branch não aprova a composição. A ausência de uma
candidata integrada é um **bloqueador P0 de entrega**, não um bug de runtime
atribuído a código que ainda não existe. Não houve merge, push em main ou resolução
de conflitos nesta auditoria. `models/semantic-v1/` permanece idêntico à baseline
em **todos os 11 heads**; não existe melhoria de pesos promovida neste ciclo.

## Matriz final T01–T15

O SHA de código de todas as linhas é [89622ec714b815c216a9215ab9ba69999b39c6b8][S].
As qualificações abaixo impedem que um teste técnico parcial aprove um requisito
que também exige execução física ou foto real.

| Requisito | Resultado | Evidência / limite | SHA |
| --- | --- | --- | --- |
| T01 — instalação limpa no PC da apresentação | **BLOCKED** | App abriu no ambiente Linux existente. PR #29 registra instalação limpa Linux separada; Windows/PowerShell e PC real não executados | [89622ec][S] |
| T02 — início/contingência sem rede | **BLOCKED** | ADV-15 executa ONNX com `socket.connect` Python bloqueado; browser bloqueia externos. Bibliotecas nativas/rede do SO e contingência no PC físico não verificadas | [89622ec][S] |
| T03 — JPG/PNG/câmera, RGB/EXIF | **BLOCKED** | Testes de imagem e ADV-04 corrigem EXIF; upload técnico passou no browser. Câmera física, negação de permissão e fotos autorizadas pendentes | [89622ec][S] |
| T04 — entrada inválida sem queda/exposição | **FAIL** | ADV-03 e BROWSER-02 recusam vazio/corrompido sem tela branca; ADV-10 demonstra que o boundary público permite detalhe bruto na UI/log. Não houve dado pessoal real | [89622ec][S] |
| T05 — filtros comparados em fotos reais | **BLOCKED** | Testes Gaussian/pixel passam; faltam duas fotos elegíveis. ADV-01 também reproduz acoplamento indevido à inferência | [89622ec][S] |
| T06 — Otsu e outro método, erros explicados | **BLOCKED** | Segmentação e máscaras degeneradas exercitadas tecnicamente. Sem fotos reais autorizadas de sombra/reflexo/transparência e sem referência humana | [89622ec][S] |
| T07 — morfologia e kernel conhecidos | **PASS** | Escopo técnico: `test_morphology.py` verifica primitivas/borda/iterações/igualdade com OpenCV; exportação registra quatro primitivas. Não mede qualidade em campo | [89622ec][S] |
| T08 — evidência da mesma execução | **PASS** | Escopo técnico: ADV-13, testes lossless e exportador oficial, hashes dos arrays e PNGs; 9 estágios no ZIP. Fotos reais ficam em T05/T06 | [89622ec][S] |
| T09 — inferência e possibilidade de corrigir erro | **FAIL** | ADV-14/15: hashes/ONNX CPU passam; ADV-08/09: encoder ausente dá erro controlado, mas desaparece o seletor manual. BROWSER-03/04 confirmam falha de continuidade após input inválido | [89622ec][S] |
| T10 — destino após confirmação, seis classes | **PASS** | Escopo técnico: testes `test_public_flow.py`/`test_disposal_targets.py` verificam classes/cores/coleta especial; BROWSER-06 confirma escolha humana Vidro → lixeira verde | [89622ec][S] |
| T11 — navegação, estado e autorização | **BLOCKED** | BROWSER-07/08/10/11 e testes de sessão/identidade passam localmente. Abas preservam análise; reload pede reenvio; contexto novo não herda foto. Dispositivos/contas reais pendentes | [89622ec][S] |
| T12 — regressão/CI no SHA | **PASS** | Escopo técnico: Ruff, 496 testes + 108 subtestes, pip check; [CI da baseline][ci-main] com PostgreSQL 16 verde. CI do PR documental deve ser conferida no seu head | [89622ec][S] |
| T13 — PC/Android/iPhone físicos | **BLOCKED** | DEVICE-01; Chromium Linux não simula aceite de aparelhos reais | [89622ec][S] |
| T14 — três demos de 10–15 minutos | **BLOCKED** | APS-REHEARSAL; os três registros abaixo continuam `manual_pending` | [89622ec][S] |
| T15 — relatório/ficha/autoria/entrega oficial | **BLOCKED** | PR #30 fornece base técnica, não submissão concluída. Faltam fotos reais, revisão/autoria privada, ficha oficial, pacote/aceite do SHA e conferência institucional | [89622ec][S] |

São **4 PASS técnicos, 2 FAIL e 9 BLOCKED** no requisito completo. Essa contagem
não é percentual de acurácia, cobertura do modelo ou probabilidade de aprovação.

## Falhas reproduzidas e severidade

| ID | Severidade / reprodução | Causa observada e menor ação necessária |
| --- | --- | --- |
| BUG-01 | **P1**, ADV-01 | Controle padrão versus Gaussiano 7×7, sigma 2, na mesma fixture: **5.525 pixels da entrada RGB do encoder mudam**; contrato padrão coincide com o modelo, contrato alterado não. [Pipeline:179][pipeline] usa `filter_result.image`; [contrato][contrato] inclui filtro interativo. Separar trilhas conforme PR #21 e repetir invariância. **Não foi medida perda de acurácia.** |
| BUG-02 | **P1**, ADV-09, BROWSER-03/04 | Com encoder ausente há erro visível e zero exceção não tratada, mas nenhuma escolha manual. Arquivo inválido também remove a escolha e a aba Descarte não a repõe. [Controller][controller] só renderiza confirmação com `result != None`. Integrar/testar fallback do PR #26, inclusive sem foto/modelo |
| BUG-03 | **P1**, ADV-10 | [Boundary][boundary] envia `technical_detail` bruto para log e `st.code`. Marcador exclusivamente sintético chega a ambos; **não é relato de incidente em produção**. Sanitizar mensagens/logs conforme PR #26, preservando código/tipo/motivo sem valor bruto |
| BUG-04 | **P2**, ADV-16 | Cache vazio é interpretado como `(None, 0)` válido durante 60 s de relógio monótono. Em 5 s o store stub nem é consultado. [Fonte][cache] e correção no PR #29; testar relógios 0/5/100 s e revogação. Fallback local permanece possível; não houve acesso remoto real |
| BUG-05 | **P1 de evidência**, ADV-17 | Inventário legado marca `AC-10=ok` sem campo independente: modelo presente, raw=0, curado=0. CLI gerou 7 relatórios e retornou 0, **não um pacote executável nem aceite**. [Fonte][pack] aprova pelo `final_model_exists`. Não usar esse `ok` para release; corrigir/qualificar inventário e preferir o pacote de revisão explícito do PR #29 |
| DOC-01 | **P2**, snapshot da API | CI de treinamento citada como qualidade nos PRs #29/#30; errata e URL correta acima. Regenerar artefatos dependentes |

Não se reproduziu violação crítica de isolamento ou descarte automático no fluxo
semântico ativo. Isso não prova ausência de vulnerabilidades: testes A/B reais e
Supabase publicado não foram autorizados/executados. Os P1 acima bloqueiam o
aceite deste candidato mesmo sem um incidente real.

As máscaras totalmente vazia/cheia **não** mudaram o RGB do encoder (ADV-02),
portanto não se registra esse comportamento como bug. Capturas uniformes preta
e branca pedem nova foto (ADV-07); isso não comprova rejeição de todo cenário real
sem objeto. Indisponibilidade do banco foi exercitada com stub (ADV-12), sem rede
ou produção. Testes existentes verificam limites de bytes/pixels antes do decode.

Plástico/vidro transparentes, metal refletivo e fundo confuso/sem objeto real
continuam **FIELD-01/02/03 BLOCKED**. Uma matriz histórica não identifica a causa
visual de uma confusão sem que a foto correspondente possa ser inspecionada.

## Modelo, baseline versus candidata e cobertura permitida

Configuração real: `semantic_onnx_assisted`, CLIP ViT-B/32 QuickGELU FP16
congelado, cabeça supervisionada local, entrada RGB 224×224, limiar **0,8** e
`confirmation_required=true`. Nenhum limiar ou safety gate foi contornado.
As verificações de integridade passaram sobre cabeça, três shards concatenados
e contrato; hashes completos em ADV-14:

| Artefato | SHA-256 |
| --- | --- |
| `semantic.json` | `5821ecf3ccc4e5b7dd807cab74978df14aae6e82a2360c765c7232bdf1fa75f2` |
| `head.npz` | `5cc1aa6b5ee4d0e0ed74bca37a8510802f739b61c5e179165beae15c68e8386a` |
| Encoder reunido | `dfad0c5b643cc67908fbfc88b7ba5ecad10aa6567cc72bfced3a759baaf509bd` |
| Contrato de processamento | `2a1a47bad72255684a7a33a3f038d6b622f120ff5ee10c6597734e27fa46a61d` |

| Comparação | Baseline | Candidata oficial examinada | Conclusão |
| --- | --- | --- | --- |
| Código | `89622ec...` | `89622ec...` | Mesma fonte; PRs não integrados |
| Pesos/contrato | Hashes acima | Mesmos hashes | Sem candidato novo promovido |
| Avaliação histórica reexecutada | 101/145 top-1; macro F1 0,6510 | Idêntica | Reprodutibilidade histórica, **não ganho** |
| Campo independente novo | Não disponível | Não disponível | Sem comparação quantitativa elegível |
| Latência comparável em campo | Não medida | Não medida | ADV-15 mediu **439,63 ms**, uma chamada CPU local com encoder já reunido, incluindo análise/carregamento. Não é p95, benchmark pareado ou latência publicada |

O relatório histórico reutiliza features de desenvolvimento; objetos/sessões
e fotos originais não acompanham o clone. Os 16 hashes reservados não têm
rótulos/features disponíveis. Mantém-se **`independent_test=false`**. Top-1 é
avaliado antes da confirmação humana, nunca substituído pela classe confirmada.

| Classe histórica | N | Precisão top-1 | Recall top-1 | F1 top-1 | Falsos positivos top-1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| battery | 14 | 75,00% | 21,43% | 0,3333 | 1 |
| electronic | 16 | 88,89% | 50,00% | 0,6400 | 1 |
| glass | 29 | 79,31% | 79,31% | 0,7931 | 6 |
| metal | 29 | 78,57% | 75,86% | 0,7719 | 6 |
| paper_cardboard | 29 | 55,00% | 75,86% | 0,6377 | 18 |
| plastic | 28 | 65,71% | 82,14% | 0,7302 | 12 |

Matriz histórica: **linhas = rótulo; colunas = previsão top-1**. Não são fotos
novas nem resultados do corpus de campo solicitado.

| Real \ Previsto | battery | electronic | glass | metal | paper_cardboard | plastic |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| battery | 3 | 1 | 1 | 2 | 7 | 0 |
| electronic | 1 | 8 | 1 | 1 | 3 | 2 |
| glass | 0 | 0 | 23 | 1 | 2 | 3 |
| metal | 0 | 0 | 3 | 22 | 2 | 2 |
| paper_cardboard | 0 | 0 | 0 | 2 | 22 | 5 |
| plastic | 0 | 0 | 1 | 0 | 4 | 23 |

No limiar do artefato, **51/145 aceitos (35,17% de cobertura)**: 47 corretos e
4 errados, precisão seletiva **92,16%**, erro seletivo **7,84%**; 94 rejeitados
(64,83%). Rejeições por classe real: battery 13/14, electronic 15/16, glass
20/29, metal 14/29, paper_cardboard 19/29 e plastic 13/28. Mesmo nesse histórico,
há um metal aceito como vidro e duas classes especiais aceitas como papel;
isso reforça a necessidade de confirmação, sem inferir causa visual.

O diagnóstico TrashNet já versionado registra 186/224 top-1 e 94 aceitos corretos,
130 rejeitados (cobertura 41,96%); **não foi reexecutado com originais nesta etapa**.
Ele também tem `independent_test=false`, não fornece grupos por objeto/sessão e
não é comparação antes/depois com o histórico de 145. O TACO local tem apenas
23 crops de treino e não serve como teste final. Não se baixaram novas imagens.

**Estados efetivamente permitidos:** no motor semântico ativo, `needs_confirmation`
para hipóteses dentro do escopo, `outside_scope`, `retake` e `needs_training`
quando o contrato diverge. Ausência do modelo produz erro controlado, não o estado
tipado `model_unavailable` do PR #24. O conjunto novo `identified/probable/
unrecognized/out_of_scope/retake/model_unavailable` ainda não está em main.

Nenhuma classe está habilitada para uma afirmação automática **“Material
identificado”** no caminho ativo. A aceitação automática do produto é **0% por
política de confirmação**; não é cobertura medida em fotos de campo. ADV-05
injeta scores 0,99 válidos nas seis classes e em `unknown` e confirma a ausência
de liberação automática; são stubs de política, não testes de acerto do modelo.
A aceitação interna do artefato não equivale à aceitação do produto. O PR #24
também traz todas as classes com `assertive=false`, sem thresholds calibrados
ou evidência independente preenchidos. Não liberar opt-in apenas para a demo.

## Execuções, smoke e evidência PDI

Python **3.12.14**, ONNX Runtime **1.31.0**, Streamlit **1.67.0**; demais versões
em `checks.json`. No ambiente atual, Ruff e pip check passaram; **496 testes e
108 subtestes passaram** em 9,23 s. A seleção pertinente de modelo, imagem,
morfologia, manifesto, sessão, identidade e serviços passou com **100 testes e
65 subtestes**. As sondas adversariais e o smoke retornam **2** para os FAIL/BLOCKED
observados; não foram convertidos em sucesso ou escondidos na contagem pytest.

O aceite estrito, com fixture técnica e stores opcionais isolados, retornou **2**:
12 `ok`, 4 `attention`, 5 `pending`, nenhuma `failed` no seu catálogo próprio.
Isso não contradiz as falhas das sondas: são coberturas diferentes. QA-09 e
QA-18..QA-21 **não estão aprovados**. PostgreSQL 16 não foi reiniciado localmente
nesta etapa por falta de espaço para container; o job isolado de qualidade foi
consultado e será repetido pela CI do PR, sem apontar para Supabase real.

O Chromium local abre visitante, faz upload técnico, permite escolher Vidro,
mostra a lixeira verde e preserva resultado/escolha entre abas. Reload cria nova
sessão e pede reenvio; não restaura análise anterior. Contexto visitante novo não
herda foto/escolha e query `profile=admin_secretaria` não libera Gestão. Não houve
erro JS/exceção não tratada; isso não equivale a isolamento de contas A/B reais.

O exportador oficial gerou **22 artefatos mais `reproduction.json`**, com o
mesmo input técnico/arrays da execução. O ZIP registra **9 estágios** e o hash
RGB coincide com ADV-01/13. Erosão/dilatação alteraram respectivamente
320/320/328/328 pixels; a máscara final voltou à contagem e aos pixels originais
nessa fixture. Isso é resultado medido, não melhoria presumida. O tempo PDI
total foi **462,97 ms** em uma execução local; não é benchmark de reconhecimento.
Não há máscara humana: **IoU/Dice de fotos reais não medidos**. Os rasters e ZIPs
técnicos ficaram em `reports/` ignorado; o Git contém metadados, não uma galeria
fictícia apresentada como sustentabilidade real.

A URL oficial continua `https://ecoscan-gabrielhamad.streamlit.app`. Nesta etapa
não houve novo smoke publicado. O registro do PR #28 informa HTTP 200 de shell,
bloqueio TLS no Chromium do ambiente e SHA/modelo efetivamente servidos não
comprovados. Nenhuma melhoria de PR foi atribuída ao deploy. A configuração
versionada permite modelo remoto; sem credenciais/runtime observado não se pode
afirmar que o site serve os mesmos pesos locais só pelo SHA do código.

## Ensaios, pacote e congelamento

| Ensaio | Dispositivo/navegador | Data, duração e ocorrências | Resultado |
| --- | --- | --- | --- |
| 1 — roteiro completo de 10–15 min | Não fornecido | Não executado; não há cronômetro/evidência | `manual_pending` |
| 2 — repetição incluindo erro e correção | Não fornecido | Não executado | `manual_pending` |
| 3 — repetição com contingência autorizada | Não fornecido | Não executado | `manual_pending` |

O [roteiro do PR #30](https://github.com/Gabrielhamad/ecoscan/blob/cb044ffab6043b4d2f153a923b6c42ddf525d35f/docs/aps/roteiro_seminario.md)
planeja 13 minutos; planejamento não conta como ensaio. Selecionar fotos antes
de olhar previsões, mostrar pelo menos um erro/rejeição e manter correção humana.

O pacote do PR #29 é de **revisão**, com `source_sha=89622ec...`, builder separado
e `release_ready=false`; o smoke Linux anterior não cobre os bugs aqui encontrados
nem autoriza Windows/PC/fotos offline. O apêndice e o DOCX do PR #30 são bases
auditáveis ainda não integradas; Arial 12/1,5/A4/margens foram conferidos em OOXML,
mas o preview usou fonte substituta por ausência de Arial. Não atestar paginação,
ficha oficial ou versão final ABNT por esse teste técnico.

A consulta GitHub retornou **zero releases** e `main.protected=false`. Não se
alterou branch protection. **Nenhuma tag/release foi criada por esta auditoria**:
não há CI/aceite de uma candidata integrada nem evidência manual suficiente.
Congela-se apenas a referência de auditoria; o produto final não está aprovado.

## Menores ações P0 para sair do NO-GO

1. Formar uma única candidata revisável: integrar as correções de trilhas e
   recuperação/sanitização (#21/#26), resolvendo as sobreposições dos PRs
   selecionados. Reproduzir ADV-01/09/10 e BROWSER-03/04 no novo SHA. Manter
   confirmação global, limiar e pesos atuais até evidência elegível de promoção.
2. Tornar inequívoca a evidência de entrega: não aceitar `AC-10=ok` por existência
   do arquivo; corrigir/qualificar BUG-05, atualizar referências de CI, executar
   Ruff/pytest/pip check/contratos/CI PostgreSQL no SHA integrado e repetir smoke.
   Adotar lock/pacote revisado com origem explícita; CI isolada de branches não basta.
3. Obter **duas fotos reais autorizadas e um caso real de falha diagnosticada**
   para PDI; registrar origem/direitos/hash/parâmetros/efeitos. Para qualquer
   assertividade por classe, exigir também corpus de campo auditado, grupos,
   calibração e validação independente; até lá a demo permanece assistida.
   Não substituir esse gate por fixtures nem fabricar resultado de campo.
4. Executar o pacote no PC da apresentação e os cenários físicos aplicáveis de
   Android/iPhone; fazer os **três ensaios cronometrados**, erro/correção/descarte
   e contingência com cópia offline autorizada. Registrar dados técnicos anônimos,
   SHA e resultado; câmera negada/contas/produção continuam pendentes até teste
   expressamente autorizado. Não fazer restore/migração destrutiva em produção.
5. Atualizar relatório, índices, figuras reais e apêndice para o mesmo SHA;
   conferir autoria/ficha/regras institucionais em cópia privada. O guard do
   PR #30 exige revisão das fontes alteradas: não apenas trocar hashes para passar.
   Só depois de CI verde, aceite explícito do SHA e gates atendidos, gerar/taguear
   a release com manifesto e rollback, sem converter pendências em PASS.

Não é necessário treinar outro encoder, produzir `.exe` ou habilitar identificação
categórica para demonstrar honestamente o programa assistido. Não se promete
aprovação da professora. Esta etapa termina no diagnóstico **NO-GO**.

Rollback deste PR: reverter apenas seu commit documental; não há migração, troca
de modelo ou efeito em produção. Os scripts recriam arquivos locais em saída
explícita; encerrar o servidor local e remover somente os arquivos temporários
criados pela reprodução. Não apagar fotos/artefatos preexistentes do grupo.

[S]: https://github.com/Gabrielhamad/ecoscan/tree/89622ec714b815c216a9215ab9ba69999b39c6b8
[plano]: https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/docs/plano_validacao_aps_4_dias.md#L7
[ci-main]: https://github.com/Gabrielhamad/ecoscan/actions/runs/42387641972
[pipeline]: https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/app/pipeline.py#L179
[contrato]: https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/image_processing/contracts.py#L12
[controller]: https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/ui/analysis_controller.py#L130
[boundary]: https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/ui/common_views.py#L20
[cache]: https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/services/published_model.py#L23
[pack]: https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/services/delivery_pack.py#L174
