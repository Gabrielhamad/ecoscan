# Captura web do dataset EcoScan

## Objetivo

Ampliar a base inicial de imagens sem depender apenas de fotos manuais do grupo, mantendo fonte, licença e possibilidade de auditoria.

## Fontes usadas

- Wikimedia Commons: `scripts/capture_wikimedia_dataset.py`
- Openverse: `scripts/capture_openverse_dataset.py`
- TACO: `scripts/capture_taco_dataset.py`

As rotas gravam manifesto com URL, licença, autor/crédito quando disponível, categoria de origem e hash SHA-256. Imagens sem rastreabilidade ou claramente ruidosas devem ficar fora do treino final.

## Estado após a captura de 2026-09-10

Total em `data/raw`: 504 imagens válidas.

| Classe | Imagens brutas | Status |
|---|---:|---|
| `plastic` | 50 | mínimo bruto atingido; revisar curadoria |
| `paper_cardboard` | 50 | mínimo bruto atingido; revisar curadoria |
| `metal` | 50 | mínimo bruto atingido; revisar curadoria |
| `glass` | 50 | mínimo bruto atingido; revisar curadoria |
| `organic` | 50 | mínimo bruto atingido; revisar curadoria alta |
| `battery` | 50 | mínimo bruto atingido; revisar curadoria |
| `electronic` | 50 | mínimo bruto atingido; revisar curadoria |
| `lamp` | 50 | mínimo bruto atingido; revisar curadoria |
| `medicine` | 41 | precisa de mais 9 imagens úteis para alvo de 50 |
| `cooking_oil` | 22 | precisa de mais 28 imagens úteis para alvo de 50 |
| `aerosol` | 21 | precisa de mais 29 imagens úteis para alvo de 50 |
| `chemical_packaging` | 20 | precisa de mais 30 imagens úteis para alvo de 50 |

Após a preparação automática, `data/processed` ficou com 499 imagens aproveitáveis:

| Classe | Imagens processadas |
|---|---:|
| `plastic` | 50 |
| `paper_cardboard` | 49 |
| `metal` | 50 |
| `glass` | 50 |
| `organic` | 50 |
| `battery` | 50 |
| `electronic` | 50 |
| `lamp` | 48 |
| `medicine` | 41 |
| `cooking_oil` | 20 |
| `aerosol` | 21 |
| `chemical_packaging` | 20 |

## Verificação visual rápida

As grades em `reports/dataset_analysis/class_examples_<classe>.jpg` mostram que:

- `plastic`, `paper_cardboard`, `metal`, `glass`, `battery` e `electronic` têm volume mínimo, mas ainda podem conter cenas amplas.
- `organic` tem boa variedade, porém exige curadoria alta porque pode misturar comida pronta, restos e contexto social.
- `lamp` atingiu volume bruto, mas perdeu duas imagens na preparação automática.
- `medicine` foi reforçada com blisters e frascos, incluindo recortes TACO.
- `aerosol` foi reforçada com imagens Openverse e recortes TACO.
- `cooking_oil` e `chemical_packaging` ficaram aceitáveis como semente, mas ainda abaixo do alvo final de 50.

## Baseline provisória

Foi gerado um split provisório a partir de `data/processed` para o app reconhecer a estrutura das 12 classes já filtradas/segmentadas:

- treino: 350 imagens;
- validação: 77 imagens;
- teste: 72 imagens.

Métricas da baseline em `reports/evaluation/baseline_test`:

- acurácia aceita: 0,069;
- macro F1: 0,111;
- incertos: 55/72.

Esse resultado baixo é esperado e tecnicamente importante: ele demonstra que volume web, baseline KNN e classes desbalanceadas não substituem curadoria e modelo final por transfer learning. O app usa aviso de confiabilidade por classe para não apresentar uma identificação fraca como certeza.

## Quarentena

Arquivos baixados antes da gravação incremental do manifesto, ou capturados com ruído evidente, foram movidos para `data/quarantine`.

| Pasta | Motivo |
|---|---|
| `data/quarantine/unmanifested_web_capture_20260909` | imagens salvas antes do manifesto final, sem rastreabilidade completa |
| `data/quarantine/noisy_openverse_20260909` | imagens de Openverse com alto ruído para óleo, aerossol e embalagem química |
| `data/quarantine/non_photographic_or_offclass_openverse_20260910` | cliparts, stickers, rótulos isolados e falsos positivos removidos da base bruta |

Esses arquivos podem ser revisados manualmente, mas não devem ser usados automaticamente no treino.

## Decisão técnica

Não foi usada captura aleatória de buscadores gerais, porque isso criaria risco de licença, rótulo incorreto e baixa reprodutibilidade. O caminho profissional é usar fontes abertas, manifesto de origem e curadoria antes do treinamento final.

## Próximos passos

1. Revisar `reports/dataset_review/review_sheet.csv`.
2. Marcar `status=accepted` apenas para imagens em que o resíduo principal está claro.
3. Corrigir `suggested_class` quando a imagem estiver em pasta errada.
4. Aplicar curadoria para `data/curated`.
5. Rodar preparação automática para `data/processed`.
6. Rodar novo split e treinamento.
7. Completar `medicine`, `cooking_oil`, `aerosol` e `chemical_packaging` até 50 imagens úteis por classe.
8. Treinar transfer learning e comparar com a baseline.

## Evidências geradas

- `reports/web_capture/wikimedia_capture_manifest.csv`
- `reports/openverse_capture/openverse_capture_manifest.csv`
- `reports/taco_capture/taco_capture_manifest.csv`
- `reports/dataset_analysis/dataset_analysis.json`
- `reports/dataset_analysis/random_examples.jpg`
- `reports/dataset_review/review_sheet.csv`
- `reports/dataset_readiness/dataset_readiness.md`
- `reports/dataset_preparation/preparation_manifest.csv`
