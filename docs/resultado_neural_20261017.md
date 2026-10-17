# Avaliacao de reconhecimento - 17/10/2026

## Trabalho executado

Foram executados dois experimentos adicionais, mantendo o preparo RGB antes
da rede e a mesma divisao por grupos da rodada de referencia:

1. SVM RBF sobre caracteristicas congeladas, com normalizacao L2 e calibracao
   sigmoid em cinco folds de grupos dentro do treino.
2. Fine-tuning real da MobileNetV2 TorchVision: saida treinada na primeira epoca
   e ultimos blocos convolucionais ajustados a partir da segunda, com perda
   balanceada, batch normalization fixa, limite de gradientes e parada antecipada.

Nenhuma imagem foi relabelada automaticamente. Originais e modelos anteriores
foram preservados. Os novos modelos nao foram ativados no aplicativo publico.

## Selecao pela validacao

| Experimento | Melhor macro-F1 de validacao |
| --- | ---: |
| Caracteristicas ONNX + regressao logistica anterior | 67,34% |
| Caracteristicas ONNX + SVM calibrada | 66,71% |
| Fine-tuning TorchVision, melhor epoca (4) | 64,20% |

A comparacao com SVM conservou a regressao logistica. O fine-tuning executou
sete epocas e parou apos tres sem melhora. A perda de treino caiu de 1,659
para 0,705, enquanto a validacao piorou depois da quarta epoca: indicio de
sobreajuste. O estado avaliado foi o da quarta epoca, nao o ultimo.

Os pesos iniciais TorchVision sao distintos do ONNX anterior. Este experimento
nao isola apenas o efeito de descongelar camadas, nem permite concluir que todo
fine-tuning seria pior. Esta configuracao nao superou a anterior.

## Avaliacao exploratoria

| Medida no teste | Candidato anterior | Fine-tuning |
| --- | ---: | ---: |
| Acerto geral | 64,83% | 54,48% |
| Macro-F1 | 65,98% | 54,37% |
| Cobertura de respostas aceitas | 31,72% | 11,03% |
| Acerto entre aceitas | 91,30% (42/46) | 100% (16/16) |

Os 100% sao apenas 16 respostas aceitas; as outras 129 foram rejeitadas.
Isso nao significa reconhecer corretamente todas as imagens. O limiar neural
0,95 foi fallback: nenhuma politica da validacao atingiu simultaneamente
90% de acerto e pelo menos 20 respostas aceitas. Temperatura escolhida: 0,5.

| Material | F1 anterior | F1 fine-tuning |
| --- | ---: | ---: |
| Pilhas | 77,42% | 55,56% |
| Eletronicos | 75,86% | 57,14% |
| Vidro | 55,56% | 48,28% |
| Metal | 75,36% | 62,96% |
| Papel/papelao | 60,71% | 59,70% |
| Plastico | 50,98% | 42,55% |

O teste foi reutilizado e e exploratorio. Grupos fisicos de objetos nao foram
fornecidos; a separacao automatica nao reconhece todas as repeticoes do mesmo
objeto. Reservar um lote novo antes de afirmar desempenho em campo.

## Casos reais conhecidos no fine-tuning

| Caso | Esperado | Hipotese | Escore | Aceita? |
| --- | --- | --- | ---: | --- |
| Garrafas PET | Plastico | Vidro | 0,824 | Nao |
| Lata vermelha | Metal | Metal | 0,724 | Nao |
| Lata alta | Metal | Pilha | 0,918 | Nao |

Os tres casos passaram pelo preparo completo. Nenhum entrou neste treinamento
ou alterou parametros depois da avaliacao. Continuam pendentes PET e lata alta.

## Decisao e proxima rodada

Conservar o candidato anterior e nao publicar o fine-tuning como melhoria.
A meta de alto acerto por material ainda nao foi atingida. Os experimentos
justificam revisar dados, cobertura e protocolo antes de multiplicar filtros.
Nao comprovam que o dataset seja o unico fator limitante.

Para a proxima rodada, revisar a identidade do objeto e do material em cada
exemplo; distinguir latas altas de pilhas e PET de vidro; incluir objetos reais
de varias cores e estados; agrupar angulos do mesmo objeto; registrar reportes
aprovados com consentimento. Treinar e avaliar com um novo lote reservado.
O [guia do grupo](guia_do_grupo.md) define variacoes de captura por material.
Luz, foco e enquadramento podem ser melhorados; uma foto nao revela sempre a
composicao do material, e filtro algum garante recuperar detalhes ausentes.

O escopo atual e de seis classes, nao de qualquer objeto reciclavel. Reconhecer
varios residuos individualmente requer anotacoes de objetos e treinamento de
deteccao. Segmentacao por contraste identifica regioes, nao comprova material.

## Reproducao e verificacao

Ver [treinamento neural](fine_tuning.md). Rodada real executada:

```powershell
tmp/finetune-env/Scripts/python.exe scripts/fine_tune_candidate.py --source ../ecoscan/data/curated --reference-run reports/training_embedding_20261016 --output reports/finetune_20261017 --epochs 8 --cases tmp/recognition_cases.csv
```

Ambiente isolado: PyTorch 2.14.1+cpu, TorchVision 0.29.1+cpu, CPU.
Artefatos locais ignorados pelo Git: `reports/finetune_20261017/` e
`reports/training_calibrated_20261017/`. SHA-256 dos pesos escolhidos:
`96fe560df9ca966bddb68f38cf2c930b727ee0ef6a943a5a3bcd1c4448fb9875`.
Fotos pessoais e pesos nao foram enviados ao repositorio.

Suite padrao: 373 testes e 82 subtestes passaram; dois itens ignorados
(permissao de symlink e modulo opcional PyTorch). No ambiente neural, os dois
testes especificos de inferencia, integridade, contrato e rejeicao passaram.
O carregador opcional foi exercitado tambem nos tres casos reais.
