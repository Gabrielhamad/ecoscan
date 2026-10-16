# Reconhecimento com caracteristicas internas

## Mudanca implementada

O treinamento agora usa, por padrao, 1280 caracteristicas internas da MobileNetV2
antes da classificacao ImageNet. O candidato anterior usava 1000 logits.
Ambos preservam preparo RGB adaptativo antes da rede e classificacao supervisionada.
O carregador distingue formatos, valida dimensoes e conserva compatibilidade com
artefatos antigos. Nenhum modelo publico foi substituido nesta rodada.

## Resultado medido

Mesmas imagens e divisao automatica por grupos da rodada anterior: 433 de treino,
145 de validacao e 145 de teste. Estes numeros descrevem esta rodada, nao o tamanho
permanente do projeto. A escolha de regularizacao ocorreu somente na validacao.

| Medida no teste | Logits anteriores | Caracteristicas internas |
| --- | ---: | ---: |
| Acerto geral | 56,6% | 64,8% |
| Macro-F1 | 57,7% | 66,0% |
| Respostas aceitas | 24,8% | 31,7% |
| Acerto entre aceitas | 88,9% | 91,3% |

O ultimo numero corresponde a 42 acertos em 46 respostas aceitas: quatro erros
continuam sendo aceitos. As outras 99 imagens foram rejeitadas pelo limiar.
Nao significa 91,3% de acerto em todas as fotos. Na validacao, o limiar 0,8
aceitou 37 respostas, com 34 acertos. Regularizacao escolhida: C=0,01.

O teste foi reutilizado para comparar arquiteturas e passa a ser exploratorio.
Reservar um novo conjunto cego antes de afirmar desempenho em uso real.
Nao foram fornecidos grupos de objeto/sessao; dHash nao elimina todas as
possiveis fotos do mesmo objeto entre conjuntos.

## Fotos reais conhecidas

| Caso | Classe esperada | Hipotese | Aceita? |
| --- | --- | --- | --- |
| Grupo de garrafas PET | Plastico | Vidro, escore 0,827 | Sim, erro |
| Lata vermelha | Metal | Metal, escore 0,370 | Nao |
| Lata alta de energetico | Metal | Pilha, escore 0,504 | Nao |

Essas fotos passaram pelo preparo completo, incluindo os diagnosticos de
segmentacao, antes da classificacao. Nao foram adicionadas ao treinamento desta
rodada. O resultado impede promover o candidato como solucao desses casos.

## Proxima melhoria orientada por evidencias

1. Revisar imagens de PET, vidro, latas altas e pilhas, identificando objeto
   principal, rotulo, fundo e variacoes. Conservar exemplos amassados validos.
2. Coletar diferentes objetos reais, com grupo de captura; reservar objetos
   inteiros para teste, incluindo cenas fora das classes suportadas.
3. Treinar com variacoes de luz e enquadramento apenas no conjunto de treino.
4. Comparar fine-tuning e deteccao com caixas anotadas. A classificacao atual
   usa a foto inteira; segmentacao por contraste nao equivale a detectar material.
5. Publicar somente apos avaliar acerto por classe, erros aceitos, cobertura,
   fotos novas e latencia. Reportes aprovados compoem rodadas supervisionadas.

O preparo deve preservar cor, proporcoes e bordas. Gaussian reduz ruido quando
adequado; mediana trata ruido impulsivo; bilateral preserva melhor bordas;
CLAHE pode melhorar contraste local. Nenhum deles ensina sozinho o material.
O antes/depois e a tecnica escolhida continuam disponiveis no processamento.

## Reproducao

Ver [procedimento e avaliacao dos casos reais](treinamento_mobilenet.md).
Artefatos locais ignorados pelo Git: `reports/training_embedding_20261016/`.
Incluem manifesto, pesos, contrato, metricas e `regression_cases.json`.
Fotos pessoais nao foram publicadas. Verificacao: 369 testes passaram,
um foi ignorado e 82 subtestes passaram; treino e inferencia reais em OpenCV 5.
A compatibilidade de selecao da camada no OpenCV 4 tem teste simulado;
validar o bundle no runtime de hospedagem antes de ativa-lo.

Referencias: [transfer learning](https://docs.pytorch.org/tutorials/beginner/transfer_learning_tutorial.html),
[validacao por grupos](https://scikit-learn.org/stable/modules/cross_validation.html).
