# Diagnostico do reconhecimento e acompanhamento

## Experimento controlado

Foram comparadas tres alternativas ao modelo publicado, usando as 446 imagens
revisadas do experimento de balanceamento, sem consultar o teste para selecionar
parametros. Os hiperparametros da cabeca foram mantidos em C=0.1 e pesos
balanceados. Nenhuma alternativa foi publicada.

| Alternativa | Acerto na validacao | Macro-F1 | Erros confiantes |
|---|---:|---:|---:|
| Modelo publicado | 101/145 | 0.6510 | 4 |
| Rede pre-treinada sem cabeca supervisionada | 86/145 | 0.5917 | 5 |
| Cabeca com normalizacao recalculada | 100/145 | 0.6316 | 4 |
| Cabeca com normalizacao preservada | 100/145 | 0.6316 | 4 |

A hipotese de resolver a regressao preservando a normalizacao nao foi confirmada.
A classificacao supervisionada atual ajuda em relacao ao comparador sem cabeca,
mas repetir o treinamento com esse lote nao melhorou o resultado. A validacao
e historica e reutilizada; nao representa precisao independente em campo.

Reproducao local, sem alterar producao:

```powershell
python scripts/diagnose_semantic_adaptation.py --seed reports/balance_training_20261023/learning_seed.npz --output reports/novo_diagnostico.json
```

## Acompanhamento na secretaria

Os proximos lotes concluidos registram numero de imagens efetivamente usadas
por material, quantidade de exemplos de validacao, acerto por material antes e
depois, Macro-F1, erros confiantes e motivos especificos de rejeicao.
Esses dados aparecem em **Central de analise > Resultados dos lotes avaliados**.
Um lote aparece uma vez mesmo quando inclui varios reportes.

Resultados antigos continuam acessiveis, mas sem inventar detalhes que nao foram
registrados. Lotes em andamento nao exibem resultados antigos como se fossem novos.
As linhas dos reportes preservam o ultimo resultado; isso nao e um historico
imutavel de todos os treinos. Os artefatos privados dos lotes continuam separados.
Aprovacao historica de um candidato nao comprova que ele ainda seja a versao ativa.

## Proxima mudanca de reconhecimento

Antes de iniciar ajuste dos pesos do encoder, completar a revisao por objeto e
uma avaliacao independente com fotos reais de celular. O treino experimental
ainda tem somente duas imagens de pilhas e uma de eletronicos. Repetir essas
imagens, aumentar artificialmente sua quantidade ou reduzir o limiar de confianca
nao corrige a falta de diversidade.

O sistema continua como classificacao assistida de um objeto principal por foto.
Nao foi implementada nesta rodada deteccao de multiplos objetos ou validacao
de precisao suficiente para orientacao autonoma de descarte.
