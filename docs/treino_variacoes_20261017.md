# Rodada de variacoes de captura - 17/10/2026

## Objetivo e implementacao

Comparar treinamento com e sem variacoes de iluminacao e inclinacao, preservando
o processamento de imagem antes da MobileNetV2 e a separacao por grupos.
Foram implementadas exposicoes via gamma 1,25 e 0,8 e rotacao de 7 graus com
canvas expandido. O processamento adaptativo recebe cada variacao e escolhe
sua filtragem. As caracteristicas neurais alimentam a regressao logistica.
Os pesos convolucionais da MobileNetV2 continuam congelados.

O manifesto registra original, hash, grupo, tecnica e filtragem. A opcao de
cache reutiliza caracteristicas originais verificadas, sem alterar a rodada
anterior. Os testes verificam determinismo, preservacao de canais, formato,
ausencia de alteracao do original e selecao exclusiva dos pais de treino.

## Experimento executado

Usados 723 originais desta rodada: 433 de treino, 145 de validacao e 145 de teste.
As 1299 variacoes derivam somente dos 433 pais de treino; nao representam novos
objetos independentes. Caminhos, hashes, grupos e splits dos originais foram
comparados com a rodada anterior e permaneceram identicos.

| Estrategia | C | Macro-F1 na validacao |
| --- | ---: | ---: |
| Originais | 0,01 | 67,34% |
| Originais | 0,1 | 66,65% |
| Originais | 1 | 62,86% |
| Originais + variacoes | 0,01 | 66,50% |
| Originais + variacoes | 0,1 | 64,86% |
| Originais + variacoes | 1 | 62,81% |

Venceu a estrategia original com C=0,01. O criterio e macro-F1 na validacao;
o teste nao escolhe estrategia ou parametros. O candidato selecionado manteve
64,83% de acerto geral, macro-F1 de 65,98%, cobertura de 31,72% e acerto de
91,30% entre as respostas aceitas no teste exploratorio. Nao houve ganho de
acerto nesta rodada. O teste reutilizado nao substitui um novo teste cego.

## Decisao tecnica

A ampliacao sintetica fica disponivel para experimentos futuros, sem ser imposta
quando piora a validacao. O modelo publico nao foi trocado. As fotos conhecidas
de PET e lata alta continuam sendo criterios pendentes de reconhecimento.

O resultado nao prova que variacoes nunca ajudam; mostra que estas tres
variacoes e este classificador nao superaram o treino original neste conjunto.
O proximo experimento deve revisar rotulos e cobertura de objetos reais e
comparar fine-tuning, que ajusta tambem os pesos convolucionais. Latas altas,
pilhas e garrafas precisam de exemplos distintos e revisados; fotos do mesmo
objeto devem permanecer no mesmo grupo. Nao mudar rotulos com base apenas na
cor ou na previsao do modelo. Deteccao de varios residuos exige caixas anotadas.

Reportes aprovados pela secretaria devem entrar em uma rodada identificada,
com consentimento e curadoria, mantendo fotos independentes para avaliacao.
O [guia do grupo](guia_do_grupo.md) descreve variacoes reais uteis por material.

## Reproducao

Comando executado na raiz, com caminhos locais relativos:

```powershell
python scripts/train_deep_candidate.py --source ../ecoscan/data/curated --backbone tmp/mobilenetv2-12.onnx --output reports/training_capture_20261017 --feature-cache reports/training_embedding_20261016 --augment
```

Artefatos completos em `reports/training_capture_20261017/`, ignorados pelo Git.
Fotos pessoais e modelos nao foram publicados. Codigo e orientacoes estao no
repositorio. Verificacao local: 371 testes e 82 subtestes passaram; um teste foi
ignorado. A rodada real executou extracao neural e treinamento em CPU.

Ver [procedimento de treinamento](treinamento_mobilenet.md) e
[comparacao anterior](resultado_embeddings_20261016.md).
