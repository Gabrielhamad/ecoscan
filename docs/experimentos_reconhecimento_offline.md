# Candidatos offline de reconhecimento

## Estado em 07/11/2026

Baseline inspecionada: `89622ec714b815c216a9215ab9ba69999b39c6b8`.
Não foi fornecido conjunto real novo com proveniência auditada e autorização de
uso para treinamento. Portanto: **NO-GO para alegação de melhoria ou promoção**.
Não foram treinados/avaliados candidatos com fotos de campo nesta entrega.

| Estratégia implementada | Resultado de campo |
| --- | --- |
| Baseline ONNX ativa, encoder CLIP ViT-B/32 congelado | Não reavaliada em dados novos |
| Regressão logística regularizada, C=0,01/0,1/1 | Não executada em dados de campo |
| Mesma cabeça com pesos de classes balanceados | Não executada em dados de campo |
| Temperatura e limiares por classe | Não executados em dados de campo |
| Treino com exposição leve versus sem augmentation | Benefício não medido em campo |

Os testes usam imagens/embeddings sintéticos e mocks **somente para validar
software e aritmética**. Não representam acurácia, suporte ou ganho real do EcoScan.
Nenhum artefato ativo, encoder publicado, limiar de produção, autenticação ou
fluxo privado `semantic_learning.run` foi alterado.

## Contrato de entrada

A CLI aceita apenas arquivos locais e um manifesto JSON com `train`, `validation`
e `test` previamente definidos. Reutiliza `audit_evaluation_manifest` para grupos,
classes, caminhos e hashes. Cada registro também exige:

- `path`, `sha256`, `rgb_sha256` (hash shape/dtype + NUL + bytes C-order do RGB orientado);
- `class_id` da release, inclusive `unknown` para negativos fora de escopo;
- `object_id`, `session_id` opacos e sem cruzamento entre splits;
- `license`: `private-consent`, `CC0-1.0`, `CC-BY-4.0` ou `CC-BY-SA-4.0`;
- `consent=true`, `source_kind=field_photo`.

O gerador de manifesto do [PR #22](https://github.com/Gabrielhamad/ecoscan/pull/22)
produz esse formato quando integrado. O pipeline também pode receber manifesto
local revisado com esses campos; não inventar proveniência para adaptar dados
históricos. Não aceita fixtures pela CLI e não inclui flag para contornar o gate.

O grupo deve obter revisão externa real e guardar documento privado autorizando
**treinamento e avaliação**, não apenas avaliação local. O recibo `audit.json`
deve seguir o [schema de auditoria](templates/offline_audit.schema.json), conter
hashes exatos do manifesto e da política, identificação opaca do revisor,
referência privada da evidência, data ISO com fuso, revisão de sobreposição conhecida
e aprovação explícita das três transformações documentadas. O programa verifica
esse vínculo e as declarações; **não autentica a identidade do revisor nem substitui
sua auditoria**. Não publicar o documento ou nomes pessoais no repositório.

Usar uma foto principal por objeto em validação e teste. Mais fotos do mesmo
objeto são admitidas somente no treino. O teste não pode coincidir com hashes
históricos conhecidos do seed publicado; validação também é protegida. Origem de
pré-treino CLIP e históricos inacessíveis não podem ser certificados pelo código.
`independent_test=false` permanece em todos os resultados.

## Duas fases

Preparar os dados conforme [avaliacao_campo.md](avaliacao_campo.md). Sem coleta e
recibo reais, **parar aqui**. Não criar atestados fictícios nem usar o seed
histórico como novo teste.

Conferir os hashes para o revisor, na raiz do projeto:

```bash
python -c "from pathlib import Path; import hashlib; print(hashlib.sha256(Path('reports/field/manifest.json').read_bytes()).hexdigest()); print(hashlib.sha256(Path('docs/templates/offline_candidate_policy.json').read_bytes()).hexdigest())"
```

Após o revisor emitir `reports/field/audit.json` para esses hashes:

```bash
python scripts/experiment_semantic_candidates.py fit \
  --manifest reports/field/manifest.json \
  --audit reports/field/audit.json \
  --policy docs/templates/offline_candidate_policy.json \
  --source /caminho/privado/fotos \
  --run ensaio-2026-11-07
```

`fit` valida/abre somente fotos de treino/validação. Não abre fotos de teste, não
computa seus embeddings nem métricas. Os metadados do manifesto inteiro são
lidos para impedir vazamento de grupos; os rótulos de teste não participam do
ajuste ou da seleção. Fotos finais permanecem sem inspeção automática nesta fase.

1. Extrai embeddings pelo `run_processing_pipeline` e `SemanticOnnxClassifier.image_features`
   existentes, com perfil oficial padrão. CLIP/normalização/prior permanecem congelados.
2. Compara baseline e 12 cabeças: 3 valores de C × pesos regulares/balanceados ×
   treino original/com exposição. StandardScaler só é ajustado no treino;
   regressão logística usa seed 42, solver padrão lbfgs, máximo 2500 iterações,
   limite de uma thread BLAS e rejeição de não convergência. O caso binário é
   convertido para dois logits simétricos. Nenhum objeto de treino em pickle.
3. Quando possível, separa a validação em **calibração e seleção** por componentes
   conectados de objetos/sessões, com seed fixa. Exige pelo menos 10 objetos por
   classe observada em cada parte. Se não houver suporte, usa toda a validação
   para seleção e registra calibração não executada; preserva temperatura 1 e
   limiar nominal 0,8 da baseline.
4. Com suporte, minimiza NLL em temperaturas fixas 0,75/1/1,5/2 sobre as
   probabilidades da mistura atual (transformação pós-modelo). Escolhe, na parte
   de calibração, o menor limiar da grade 0,5/0,6/0,7/0,8/0,9/0,95/1 que tenha
   precisão aceita ≥0,95 e pelo menos 10 objetos aceitos por classe. Sem limiar
   com suporte, aquela classe abstém-se (`null`). Unknown nunca é aceito. Compara
   também baseline calibrada, sem ajustar sua cabeça.
5. Compara todas as variantes e baseline **na mesma parte de seleção**. Escolhe
   entre as que passam nos gates por macro F1, depois precisão aceita, cobertura
   e nome estável. Nenhum parâmetro é escolhido pelo teste final.

A taxonomia completa de sete saídas entra na macro F1; classes sem suporte
aparecem com zero e bloqueiam o gate global. Uma coleta só das três prioritárias
pode diagnosticar candidatos, mas não aprova substituir uma release de seis
materiais sem avaliar os demais e os negativos.

Se a validação registrar `NO-GO`, manter o atual, não abrir o holdout e revisar
hipóteses usando apenas treino/validação. Se registrar `FROZEN_FOR_SINGLE_TEST`,
conferir hashes e congelamento antes de executar:

```bash
python scripts/experiment_semantic_candidates.py test \
  --manifest reports/field/manifest.json \
  --audit reports/field/audit.json \
  --policy docs/templates/offline_candidate_policy.json \
  --source /caminho/privado/fotos \
  --run ensaio-2026-11-07
```

Essa fase reconfere código, ambiente, baseline, dados, auditoria, política,
pesos e regras congeladas. Reserva o conjunto final **antes de abrir qualquer
foto de teste**, via criação exclusiva em `models/candidates/test-ledger/`,
identificada pelos hashes RGB orientados, independentemente do nome da execução.
Reservas por imagem também impedem reutilizar parte de um holdout anterior ou
apenas recodificar arquivos sem mudar pixels. Conflitos/falhas de reserva podem
consumir fotos novas parcialmente; nunca se apagam reservas automaticamente.
Avalia baseline e somente o candidato escolhido, na mesma amostra sem augmentations.
Uma falha depois da reserva também consome o holdout: não há retry/reset automático.
Uma revisão externa deve decidir um novo holdout e registrar qualquer incidente.

Não apagar/copiar o ledger para repetir teste ou selecionar outro candidato.
Esse é um controle local contra reuso acidental, não armazenamento inviolável
contra alguém que controla o filesystem. Ele não conhece testes executados em
outras máquinas: centralizar o ledger e o registro humano da avaliação do grupo.

## Métrica e gates

A [política versionada](templates/offline_candidate_policy.json) usa o ganho de
macro F1 de **mais de 0,005** do gate já existente e critérios conservadores:

- nenhum recall de classe pode cair; cobertura global e por referência de classe não pode cair;
- precisão aceita global e de cada material predito ≥0,95 e não inferior à baseline,
  com pelo menos 10 aceitos no total;
- pelo menos 10 objetos e duas sessões por classe, incluindo unknown, em seleção
  e depois no teste. Suporte é original; augmentations não contam;
- nenhum aumento em erros aceitos ou confusões graves aceitas: plástico↔vidro,
  pilhas/eletrônicos enviados a recicláveis regulares e fora de escopo aceito;
- tempo da cabeça por imagem ≤1,25× baseline + 1 ms, na mesma amostra.

O custo do encoder é comum a todas as variantes. Tempos da cabeça usam embeddings
já extraídos; não são latência total em celulares. JSON registra carga do encoder,
tamanho dos arrays e pico RSS do **processo inteiro** em Linux (null em outros
sistemas), não RAM isolada de cada modelo. Tempo de embeddings do teste inclui
I/O de cache e não é benchmark frio do encoder. Não se usa nenhum modelo adicional,
PyTorch ou dependência nova no runtime web.

Esses números são uma política técnica inicial, não garantia estatística de
produção. Alterá-los exige revisão separada antes da seleção; a CLI recusa outra
política. Há ruído de medição de latência e variação entre bibliotecas/hardware;
pesos e ranking por métricas são reproduzíveis no mesmo ambiente, tempos não são
bit a bit. Sem ganho/sem suporte, o resultado é `NO-GO`.

## Cache, artefatos e privacidade

`models/candidates/` já é ignorado por `models/*`; não versionar fotos,
embeddings, pesos candidatos ou documentos privados. A chave do cache inclui
hash da foto + encoder + contrato + augmentation + código + versões de bibliotecas.
Cada embedding tem checksum, validação de dimensão/dtype/finitude e leitura sem
pickle. Cache corrompido falha; hit não contorna validação da foto original.

O nome da execução não pode existir previamente. Saídas locais:

- `*.npz`, `*.candidate.json`: arrays, hashes e regras por variante;
- `freeze.json` e checksum: pesos/regras selecionados, hashes dos inputs, código,
  ambiente, encoder, contrato, licença CLIP e licenças dos dados;
- `validation.json/.md`: todas as comparações, recalls/matrizes, precisão aceita,
  cobertura, erros graves, suporte original, latência e motivos de NO-GO;
- `final.json/.md`: apenas baseline/candidato na única execução final, decisão,
  hashes e `published=false`;
- `test-ledger/`: reserva persistente do teste, inclusive quando abortado.

Formatos `ecoscan-offline-candidate-v1` e `ecoscan-offline-freeze-v1` **não são
releases aceitas pelo runtime**. Temperatura/limiares por classe não são aplicados
ao produto. Mesmo `ELIGIBLE_FOR_REVIEW` não publica nem autoriza reconhecimento
assertivo: integração, avaliação por classe, aprovação e eventual promoção são
outra mudança revisável. `NO-GO` mantém integralmente a release ativa.

Exposição multiplica pixels RGB por 0,9 e 1,1 com arredondamento/clipping, antes do
pipeline oficial, sobre cópias temporárias com EXIF já corrigido. Não corta objeto,
não muda matiz, não aplica máscaras e não altera a foto original. Pode apagar
informações em extremos: aprovação externa dessas opções é obrigatória; benefício
não é presumido. Só treino recebe essas variações; seleção/teste usam originais.

## Validação técnica e rollback

```bash
python -m pytest tests/test_offline_candidates.py -q
python -m ruff check src scripts tests
python -m pytest -q
python -m pip check
```

Testes verificam pesos reproduzíveis, baseline intacta, cache por identidade,
calibração com e sem suporte, invariância do suporte original e gates de regressão.
A máquina de estados é testada com injeção de dependências e fixtures explicitamente
sintéticas; a CLI pública não oferece esse bypass. Não foi emitido recibo de
origem real nesta entrega e nenhum resultado sintético foi promovido a evidência.
Um smoke técnico com ONNX CPU real confirmou embedding, dtype e probabilidades
baseline idênticos entre extração direta e cache para um RGB sintético; não houve
treino ou métrica de campo nessa verificação.

Rollback: reverter este PR; nenhum dado/banco/modelo ativo precisa ser restaurado.
Manter qualquer ledger real para não esquecer uso de holdout. Próximo gate:
coleta nova auditada, consentimento para treino/avaliação e revisão dos splits.
