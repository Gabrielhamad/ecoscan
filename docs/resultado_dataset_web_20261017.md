# Treinamento com imagens publicas - 17/10/2026

Foram baixadas e importadas 2358 imagens TrashNet, com origem, licenca, hashes
e mapeamento de classes. Os 723 originais foram preservados. As novas imagens
entraram somente no treino; validacao e teste permaneceram com 145 fotos cada.
Ver [fonte, importacao e reproducao](dataset_web.md).

## Experimentos realizados

Primeiro: comparar regressao logistica e SVM calibrada na mistura completa.
Venceu SVM RBF, C=1, com macro-F1 de validacao de 61,61%. O teste exploratorio
teve acerto geral de 61,38% e macro-F1 de 61,33%. O limiar 0,95 aceitou apenas
uma das 145 respostas (correta); nao demonstrou utilidade para reconhecimento
automatico. A validacao tambem so aceitou uma resposta nesse limiar.

Segundo: comparar referencia e ponderacao por origem. Melhores regularizacoes
de cada estrategia, escolhidas pela validacao:

| Estrategia | Macro-F1 de validacao |
| --- | ---: |
| Mistura completa, regressao logistica | 58,37% |
| Referencia sem fotos novas | 67,34% |
| Fotos externas com massa de 25% por classe | 64,52% |
| Fotos externas com massa de 100% por classe | 62,24% |

Venceu `reference_only`, C=0,01. Esse candidato foi ajustado nos 433 originais
de treino, conservando os resultados anteriores: acerto geral de 64,83%,
macro-F1 de 65,98%, cobertura de 31,72% e 91,30% de acerto entre aceitas.
Os 2791 arquivos disponiveis no split de treino nao significam que todos
foram usados pelo candidato vencedor. As fotos novas foram efetivamente
usadas nos demais candidatos, inclusive nas duas misturas ponderadas.

Nao houve aumento de acerto global nesta rodada. Nenhum modelo publico foi
substituido. Os dados novos permanecem disponiveis para revisao e experimentos.

## Resultados por material

| Material | F1 anterior | F1 mistura completa, SVM |
| --- | ---: | ---: |
| Pilhas | 77,42% | 60,87% |
| Eletronicos | 75,86% | 64,00% |
| Vidro | 55,56% | 60,71% |
| Metal | 75,36% | 73,85% |
| Papel/papelao | 60,71% | 56,72% |
| Plastico | 50,98% | 51,85% |

Houve ganhos exploratorios em vidro e plastico, mas perdas em outras classes.
TrashNet nao fornece novas fotos de pilhas ou eletronicos nesta importacao.
Sua captura em fundo claro representa um dominio diferente das cenas do
projeto. O resultado e compativel com diferenca de dominio e cobertura; nao
prova que qualquer imagem de internet seja inadequada nem identifica uma
causa unica para os erros.

## Fotos reais conhecidas

O candidato da mistura completa acertou a hipotese em uma das tres fotos
conhecidas e rejeitou as tres. O candidato selecionado da referencia tambem
acertou uma hipotese, mas aceitou indevidamente PET como vidro, como antes.
As fotos nao entraram no treino e nao ajustaram parametros depois do teste.

O lote de teste foi reutilizado em comparacoes e e exploratorio. As proximas
fontes precisam incluir cenas reais e objetos distintos, com rotulos revisados
e agrupamento de captura. Novas bases devem passar pelo mesmo protocolo antes
de serem adotadas. Separar novo lote de objetos para o aceite final.

## Evidencias e verificacao

Arquivos locais ignorados pelo Git:

- `data/raw/trashnet_20261017/`: ZIP e licenca oficiais.
- `data/curated/web_20261017/`: originais, fotos novas e proveniencia.
- `reports/training_web_20261017/`: primeiro treino, metricas e regressoes.
- `reports/training_web_balanced_20261017/`: comparacao ponderada e regressoes.
- `reports/web_processing_20261017/`: 22 artefatos de preparo de uma foto nova.

Na amostra visual de uma lata, o filtro automatico escolheu preservar a imagem
sem suavizacao; GrabCut e abertura/fechamento produziram diagnosticos de
segmentacao. A entrada neural preservou RGB e proporcoes, sem aplicar a mascara.
As demais fotos registram suas proprias decisoes no manifesto do treinamento.
Inspecao de amostras nao equivale a revisar todos os rotulos individualmente.

Verificacao: 376 testes e 82 subtestes passaram; dois itens foram ignorados.
Os testes cobrem pesos por origem, integridade da referencia, preservacao dos
splits e impedimento de novas fotos em grupos reservados. Imagens e modelos
permanecem locais; codigo, fontes e resultados foram preparados para o GitHub.
