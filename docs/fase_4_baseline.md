# Fase 4: preparação de dados e baseline

## Objetivo

Preparar o dataset para treinamento e criar uma baseline simples antes do modelo final com transfer learning.

## Separação treino/validação/teste

Script: `scripts/split_dataset.py`.

Configuração atual:

- treino: 70%;
- validação: 15%;
- teste: 15%.

O script copia imagens de `data/raw` para:

- `data/train`;
- `data/validation`;
- `data/test`.

Duplicatas exatas por SHA-256 são mantidas no mesmo split para reduzir risco de vazamento entre treino e teste. Duplicatas quase idênticas ainda exigem revisão manual ou técnica perceptual em fase posterior.

## Baseline implementada

Script: `scripts/train_baseline.py`.

A baseline principal é um KNN por características visuais simples:

- média RGB;
- desvio padrão RGB;
- histogramas RGB;
- densidade simples de bordas;
- metadado geométrico simples após redimensionamento.

Também existe suporte a centróide mais próximo para comparação, mas o KNN é melhor para o dataset semente porque cada classe contém objetos e cenários muito variados.

Essa baseline não substitui CNN nem transfer learning. Ela serve para comparação acadêmica: o modelo final precisa superar esse ponto de partida.

## Limiar de incerteza

A baseline já possui rejeição por probabilidade prevista. O limiar atual é `0.45`, separado do limiar do modelo final.

No KNN, a probabilidade é calculada por votos ponderados pela distância entre características. Ela deve ser tratada como score comparativo interno da baseline, não como confiança calibrada equivalente a uma rede neural.

Quando a maior probabilidade fica abaixo do limiar, a predição é registrada como `__uncertain__`.

Os relatórios registram dois cenários:

- `raw_top1`: sempre escolhe a classe mais próxima;
- `with_rejection`: aplica o limiar e marca predições incertas como `__uncertain__`.

## Execução

```powershell
python scripts\split_dataset.py --overwrite
python scripts\train_baseline.py
```

## Relatórios

Os resultados são salvos em:

- `reports/dataset_split/split_manifest.json`;
- `models/baseline_classifier.json`;
- `reports/baseline/validation_metrics.json`;
- `reports/baseline/test_metrics.json`;
- `reports/baseline/validation_predictions.csv`;
- `reports/baseline/test_predictions.csv`;
- `reports/baseline/baseline_summary.json`.

## Limitação esperada

Como o dataset semente do Wikimedia Commons contém imagens ruidosas e poucas amostras por classe, a baseline pode ter desempenho baixo. Isso é aceitável nesta fase e deve ser usado no relatório para justificar:

- revisão do dataset;
- filtros/segmentações mais adequados;
- uso futuro de transfer learning.

## Resultado inicial observado

Execução com o dataset semente de 140 imagens:

- treino: 98 imagens;
- validação: 21 imagens;
- teste: 21 imagens.

Métricas da baseline KNN:

- validação `raw_top1`: accuracy 0.286, macro F1 0.290;
- validação com rejeição: accuracy 0.095, 16 incertas em 21;
- teste `raw_top1`: accuracy 0.190, macro F1 0.114;
- teste com rejeição: accuracy 0.095, 16 incertas em 21.

Interpretação:

- a baseline está funcionando tecnicamente, mas o dataset semente é insuficiente para classificação confiável;
- a rejeição por incerteza evita várias respostas forçadas;
- o modelo final com transfer learning deverá superar claramente esses números;
- antes do treinamento final, é necessário limpar imagens ruidosas e aumentar a quantidade por classe.
