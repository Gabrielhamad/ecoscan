# Treinamento neural supervisionado

O ciclo `fine_tune_candidate.py` prepara cada foto com o pipeline RGB do EcoScan
antes de treinar uma MobileNetV2. Diferentemente do extrator congelado, atualiza
os pesos dos ultimos blocos convolucionais, alem da saida para residuos.

## Ambiente isolado

PyTorch e TorchVision sao dependencias opcionais de treinamento. Nao fazem parte
do ambiente padrao do Streamlit. Na raiz do projeto:

```powershell
python -m venv --system-site-packages tmp/finetune-env
tmp/finetune-env/Scripts/python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
tmp/finetune-env/Scripts/python.exe scripts/fine_tune_candidate.py --source data/curated --reference-run reports/treino_referencia --output reports/treino_neural --epochs 8
```

O uso de `--system-site-packages` reaproveita as dependencias do EcoScan
previamente instaladas. A instalacao de PyTorch fica no ambiente isolado.
Os pesos oficiais `MobileNet_V2_Weights.IMAGENET1K_V2` sao baixados no diretorio
da rodada, sem exigir GPU ou servico pago. Esta arquitetura inicial usa pesos
TorchVision distintos do backbone ONNX das rodadas anteriores; a comparacao
nao isola apenas o efeito de descongelar camadas.

## Preparacao e dados

A rodada de referencia precisa conter manifesto verificado e contrato de
processamento atual. Originais devem manter seus hashes. O script verifica
caminhos, classes e ausencia de grupos compartilhados entre splits. Nao
reescolhe o teste depois de observar os erros. Fotos do mesmo objeto ainda
exigem grupos de captura corretos na rodada de referencia; dHash e insuficiente
para identificar todos os objetos repetidos.

O preparo inclui orientacao, RGB, proporcoes, filtros adaptativos e letterbox.
Os diagnosticos de segmentacao sao dispensados no lote porque nao alteram os
pixels de reconhecimento, conforme teste de equivalencia. `preparation.json`
registra a filtragem e a origem. A normalizacao ImageNet ocorre uma vez.
Nao ha aumento sintetico nesta rodada: a comparacao anterior nao demonstrou
beneficio das variacoes implementadas. Fotos originais permanecem intactas.

## Treinamento e selecao

Primeira epoca: treina a saida com AdamW e taxa 0,001. A partir da segunda,
descongela os blocos `features[14:]`, com taxa 0,00001, e usa 0,0001 na saida.
As estatisticas de batch normalization permanecem fixas. A perda pondera as
classes pela frequencia de treino; gradientes sao limitados para estabilidade.
O treinamento usa CPU, quatro threads e seeds registrados no codigo.

O melhor estado e escolhido por macro-F1 na validacao, com parada apos tres
epocas sem melhora, respeitando pelo menos quatro epocas. O maximo e definido
por `--epochs`. A escolha pode conservar a primeira epoca se as seguintes
piorarem: realizar fine-tuning nao garante que o checkpoint escolhido tenha
superado a rede congelada.

Uma temperatura entre 0,5 e 3 e escolhida pelo log-loss da validacao; o limiar
de rejeicao usa o mesmo protocolo das rodadas anteriores. Essa validacao ja
participa da selecao do modelo, portanto nao equivale a uma calibracao externa
independente. Escores continuam sendo estimativas que precisam de avaliacao.

## Avaliacao e artefatos

`training_summary.json` registra historico, medidas por classe, matriz de
confusao, cobertura e acerto das respostas aceitas. O teste reutilizado nas
comparacoes e exploratorio; reservar outro lote de objetos para o aceite.
Nao interpretar uma media alta como sucesso em todos os materiais.

`--cases CSV` testa regressoes conhecidas depois de escolher pesos, temperatura
e limiar; usa o preparo completo do aplicativo. CSV: `path,expected_class`.
Esses resultados nao mudam automaticamente os parametros do treinamento.

O bundle local contem `fine_tuned.pth` e `fine_tuned.json`, com hash dos pesos,
classes e contrato. O carregador opcional usa `weights_only=True` e confere
integridade e compatibilidade. Nao ativa o candidato no aplicativo nem exige
PyTorch dos usuarios. Integracao e publicacao dependem de desempenho medido
por material e latencia no ambiente de hospedagem.

O treinamento cobre seis categorias: metal, plastico, vidro, papel/papelao,
pilhas e pequenos eletronicos. Nao identifica automaticamente todo reciclavel
ou varios objetos separados. Oleo e medicamentos continuam no fluxo educativo.

## Comparacao com SVM

O ciclo de extracao congelada oferece `--heads compare`: regressao logistica
versus SVM RBF com vetores normalizados. A SVM recebe calibracao sigmoid com
cinco folds de grupos, exclusivamente dentro do treino. Fotos do mesmo grupo,
incluindo variacoes, permanecem no mesmo fold. Validacao externa escolhe o
classificador. O processo conserva a regressao quando ela tem melhor macro-F1.

Fontes: [transfer learning e fine-tuning](https://docs.pytorch.org/tutorials/beginner/transfer_learning_tutorial.html),
[calibracao de classificadores](https://scikit-learn.org/stable/modules/calibration.html),
[SVC](https://scikit-learn.org/stable/modules/generated/sklearn.svm.SVC.html).
