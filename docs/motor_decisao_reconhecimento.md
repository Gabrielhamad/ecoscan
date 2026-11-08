# Motor de decisão visual — 08/11/2026

Baseline: `89622ec714b815c216a9215ab9ba69999b39c6b8`. O classificador ONNX, o encoder,
os pesos, o limiar 0,8 do artefato e `confirmation_required=true` são preservados.
Não há dados novos independentes aprovados nesta entrega. **Todas as classes
continuam com assertividade desativada.** Não existe ganho de acurácia medido aqui.

## Antes e depois na mesma hipótese

| Caso | Antes | Depois |
| --- | --- | --- |
| Metal com vetor válido, sem gate independente | Estado `needs_confirmation`, título genérico “Material sugerido para conferência” e subtítulo de material na UI | `probable`: **Melhor correspondência: METAL**. **Confirme para descartar** |
| Gate independente completo, perfil e captura válidos, limiar/margem/escopo aprovados | O motor assistido continuava sempre genérico | `identified`: **Material identificado: METAL**, ainda com confirmação antes da destinação |
| Sem hipótese utilizável/vetor inválido/empate | `uncertain` ou orientação genérica | `unrecognized`, escolha manual disponível |
| Unknown/fora do escopo | Aviso sem destinação | `out_of_scope`, sem categoria sugerida; escolha manual disponível |
| Captura escura/borrada | Recomendação de nova captura | `retake`, com opção de refazer ou corrigir manualmente |
| Arquivo inválido ou modelo indisponível | Erro interrompia a tela antes do seletor de material | `retake`/`model_unavailable`, erro seguro **e** seletor manual |
| Pilhas/baterias e eletrônicos | Confirmação assistida | Sempre `probable` ou estado de rejeição; coleta especial e confirmação explícita |
| Política revogada durante a sessão | Resultado em cache sem política por classe | Reavaliação da política/evidências em cada renderização; revogação remove a mensagem categórica sem nova inferência |
| Câmera ao vivo | Mensagens derivadas de `accepted`; regiões podiam receber o material da foto inteira | A mesma decisão do serviço governa o texto; regiões são somente “Região visual”; link de correção permanece visível |

A linha de `identified` é demonstrada apenas em testes com documentos sintéticos.
Não há gate real ativado nem evidência de campo criada por esses testes.
A análise não comprova composição química, limpeza, conteúdo ou contaminação.
Mesmo uma hipótese errada com score alto pode acontecer: o runtime não conhece o
rótulo real. Correção permanece disponível, inclusive após `identified`.

## Contratos e responsabilidades

- `RecognitionInput` é a entrada tipada, anterior à confirmação humana.
- `decide_recognition` é puro, sem Streamlit, contas, arquivos ou banco; produz
  somente `identified`, `probable`, `unrecognized`, `out_of_scope`, `retake`,
  `model_unavailable`.
- `recognition_policy.py` carrega e valida política/evidências privadas por hash.
  `decision_for_result` adapta o resultado de análise e carrega a política atual.
- `analysis_service.py` preserva `artifact_accepted` e `artifact_threshold` antes
  de aplicar a confirmação global. A aceitação final continua falsa na release
  assistida. UI e live não decidem por `accepted`, score ou tipo de modelo.
- `decision_from_error` transforma falhas em estados seguros, sem texto técnico
  privado. Arquivos inválidos são `retake`; falhas de modelo/análise são
  `model_unavailable`. A API existente continua lançando exceções para seus
  consumidores técnicos; os controladores usam o adaptador para a apresentação.
- As duas UIs reconsultam a decisão atual; a decisão anexada ao resultado é um
  snapshot para auditoria, não autoridade para manter opt-in revogado em cache.

A melhor correspondência aparece quando há vetor completo normalizado finito,
hipótese no escopo, score coerente com o topo e um vencedor sem empate. Esse texto
não é afirmação de composição nem de probabilidade estatística. Falhas de imagem,
modelo, compatibilidade ou escopo prevalecem sobre um score alto. Qualidade
`attention`/ausente permite no máximo correspondência para confirmação; nunca
`identified`. Escuridão/desfoque detectados na imagem original exigem nova captura.

`allow_disposal_guidance` permanece falso nos seis estados e
`requires_confirmation`/`can_correct` verdadeiros. Apenas a categoria selecionada
explicitamente pela pessoa abre as instruções existentes. Visitantes têm correção
local; persistir uma contribuição continua exigindo conta, consentimento e as
regras de autorização existentes. Nenhuma arquitetura de autenticação foi mudada.

## Opt-in por classe, sem atalhos

`config/settings.json` aponta para `config/recognition_policy.json`. Cada classe
possui `assertive`, `threshold`, `min_margin`, `max_unknown_score` e referência de
`evidence`. Na configuração entregue, `assertive=false` e parâmetros de opt-in
são nulos. Score alto, `reliability.is_sufficient`, `accepted=True`, alteração do
argumento legado `action_confidence_threshold` ou somente ligar `assertive` não
substituem o gate. O argumento legado continua aceito/validado por compatibilidade,
mas não habilita uma mensagem categórica.

Ativação futura exige uma mudança revisada de configuração, depois de avaliação
externa real. Colocar documentos privados em `reports/recognition_evidence/`
(ignorado por `reports/*`); política contém somente caminhos relativos e hashes.
Não colocar fotos, nomes pessoais ou dados de participantes no Git.

1. **Gate por classe:** `schema_version=1`, `class_id`, `approved=true`, referência
   opaca de aprovação, `policy_version`, `engine_version` e `engine_sha256`.
   Referências `evaluation`, `calibration`, `source_audit` possuem `path`/`sha256`.
   O [schema estrutural](templates/recognition_gate.schema.json) não é um atestado.
2. **Relatório de avaliação:** `source_kind=field_photo`, `independent_test=false`
   mantido, `integrity` com manifesto/modelo/encoder/cabeça/processamento,
   `counts` por classe/unknown, `top1.by_class` e `accepted.by_class`.
3. **Avaliação da regra exata:** o relatório inclui
   `decision_evaluation[class_id]` com `reference_objects`, `identified_objects`,
   `correct_objects`, `temperature`, `threshold`, `min_margin`,
   `max_unknown_score`, `calibration_sha256`, `engine_sha256`, `policy_version`.
   Deve medir decisões do mesmo motor e regra no conjunto independente, não apenas
   copiar precisão da classificação bruta. Cobertura/correção por objeto usam uma
   foto principal predefinida; contagens precisam ser inteiros coerentes.
4. **Calibração separada:** `class_id`, `method=temperature_scaling`,
   `split=validation`, `held_out=true`, `manifest_sha256` diferente do teste,
   `integrity` dos mesmos artefatos, temperatura, limiar, margem, teto de unknown,
   contagem de objetos/sessões e ECE medidos. Não ajustar regra no teste final.
5. **Auditoria externa separada:** `approved`, `independence_reviewed`,
   `object_session_splits_reviewed`, `consent_reviewed`, `decision_rule_reviewed`
   verdadeiros, `evaluation_manifest_sha256`, `calibration_manifest_sha256` e `reviewer_id` opaco vinculados à
   evidência real privada. Código valida declarações e hashes; **não autentica o
   revisor nem verifica por si só a verdade da origem**. Administração do deploy
   e revisão humana da aprovação são parte da fronteira de confiança.

Para obter o hash do motor antes da avaliação/aprovação:

```bash
python -c "from ecoscan.services.recognition_policy import decision_code_sha256; print(decision_code_sha256())"
```

Ele cobre verificador/política, decisão/adaptação, produtor da análise,
classificador e preparação de imagem. Alterações nesses fontes invalidam a
aprovação anterior; não editar hashes para reaproveitar um aceite antigo.
Mudanças somente na política também devem ter versão e evidência coerentes.
Uma atualização de modelo, encoder, cabeça ou preparação exige novo vínculo.

Os pisos iniciais versionados são: 30 objetos e 3 sessões por classe na avaliação
e na calibração, 10 objetos unknown, precisão aceita e precisão das identificações
≥0,95, recall ≥0,8, ECE ≤0,1 e 30 identificações independentes para avaliar a regra.
São critérios técnicos iniciais conservadores, **não certificação estatística**
nem substituto de representatividade/auditoria. A coleta inicial de 10–15 objetos
por classe proposta para diagnóstico não autoriza identificação assertiva.

## Calibração, margem e abstenção

A temperatura atua no vetor inteiro: `softmax(log(max(score, 1e-12)) / T)`.
Com T=1, preserva-se o vetor sem alteração numérica. Ela não muda o material de
maior score; pode mudar sua escala e a margem. O serviço exige simultaneamente:

- gate aprovado da classe vinculado aos artefatos e código atuais;
- captura `good`, compatibilidade e escopo válidos;
- aceitação **original do artefato** e score acima de seu limiar (0,8 na baseline);
- score transformado ≥ limiar da classe, margem top-1/top-2 ≥ mínimo e score de
  unknown ≤ teto, conforme a regra independente medida.

Temperatura/ECE não transformam score em certeza de acerto individual. ECE depende
da amostra, bins e procedimento do avaliador; valores baixos não garantem segurança
sob mudança de iluminação, aparelho, reflexos ou distribuição. Os relatórios e sua
auditoria devem documentar isso. Na ausência de suporte, não simular calibração.
Plástico/vidro transparente e metal refletivo não têm heurística de identificação
por transparência/cor: usam os mesmos gates e exigem cenários representativos.

Política/evidência ausente, inválida, adulterada, enfraquecida abaixo dos pisos ou
revogada falha de modo fechado: nenhuma mensagem categórica, preservando uma
correspondência válida para confirmação quando possível. Arquivos externos à pasta
privada e escapes por symlink são recusados. Pilhas/baterias/eletrônicos não ganham
`identified` neste contrato, mesmo com um opt-in acidental.

## Motivos privados, observabilidade e privacidade

`decision_reason`, versões e hashes ficam no resultado técnico e nos eventos
`recognition_decision` do logger do servidor. São códigos fixos, sem foto, caminho,
conta, texto livre ou identidade de revisor. A API live só exporta apresentação,
estado e possibilidade de correção, sem scores, motivos ou documentos privados.
Erros de upload/modelo não expõem o detalhe técnico/traceback no Streamlit.

`decision_metrics_snapshot()` oferece total, contagem por estado, rejeições,
`rejection_rate` e `identified_rate` por processo. Rejeição inclui `unrecognized`,
`out_of_scope`, `retake`, `model_unavailable`. São tentativas de análise, não
acurácia, usuários únicos ou objetos independentes; zeram no reinício. Rerender
sem nova inferência não incrementa esses contadores. Não há nova telemetria remota,
persistência obrigatória ou captura de fotos.

## Validação e próximo gate

```bash
python -m pytest tests/test_recognition_decision_policy.py tests/test_recognition_safety.py tests/test_current_recognition.py tests/test_decision_ui.py tests/test_decision_live_camera.py -q
python -m ruff check src scripts tests
python -m pytest -q
python -m pip check
```

A cobertura inclui limiar/margem, calibração com efeito real na escala, vetores
inválidos/unknown, previsões plausíveis certas/erradas sem oráculo de rótulo real,
artefatos divergentes, opt-in sem prova, luz/foco, transparência, coleta especial,
visitante/conta, falhas e revogação durante cache. Documentos de prova dos testes
são fixtures sintéticas temporárias: não são avaliação independente nem autorização
para ativar as classes entregues.

Risco de regressão: consumidores técnicos dos estados antigos precisam migrar;
web/live desta versão estão atualizados. Os campos anteriores do resultado de
análise permanecem, com campos adicionais de aceitação original e decisão.
Rollback: reverter o commit; não há migração ou artefato publicado a restaurar.
Revogação imediata: desligar opt-in da classe ou remover a evidência privada;
a próxima decisão/renderização não mantém a categoria categórica em cache.

Próximo gate: avaliação independente real e aprovação por classe antes de qualquer
opt-in. Nenhuma classe foi habilitada nesta etapa; não avançar automaticamente.
