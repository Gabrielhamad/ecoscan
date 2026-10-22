# Experimento de reconhecimento: base corrigida

## Objetivo e limites

Comparar candidatos realmente treinados com o SVM distribuido no repositorio,
sem substituir automaticamente o modelo publico. A avaliacao usa o conjunto
historico fixo: ele ja foi consultado em experimentos anteriores e nao e um
teste cego de aceitacao. O eventual uso dessas imagens pelo SVM antigo nao foi
descartado. As metricas nao representam precisao garantida para a populacao.

## Dados e preparacao

- 723 imagens de referencia, com divisao original preservada.
- 23 novas imagens TACO revisadas, adicionadas exclusivamente ao treino.
- 98 exclusoes de treino mantidas conforme a curadoria por objeto.
- 358 originais elegiveis para ajustar os candidatos; 145 imagens de validacao
  e 145 de teste historico. As classes pilhas e eletronicos continuam com apenas
  dois e um exemplos originais elegiveis, respectivamente.
- Mesmo contrato de processamento do aplicativo: orientacao, RGB, preservacao
  das proporcoes, escolha conservadora de filtros e entrada 224 x 224.
- Mascaras de segmentacao nao substituem os pixels da entrada do classificador.
  A renderizacao diagnostica das mascaras e omitida no processamento em lote.
- Grupos declarados de origem, hashes e deteccao heuristica de duplicatas
  impedem misturas conhecidas entre treino, validacao e teste. Isso nao prova
  que todos os objetos fisicos sejam independentes.

## Candidato MobileNetV2

Extracao convolucional pre-treinada de 1.280 caracteristicas e ajuste de uma
regressao logistica. Foram comparadas tres regularizacoes e duas estrategias
elegiveis: originais revisados e originais com 1.074 variacoes de luminosidade
e inclinacao. As variacoes foram geradas somente a partir do treino.
O comparador sem exclusoes foi medido como diagnostico e impedido de vencer
a selecao. Os pesos convolucionais permaneceram congelados; esta etapa nao
foi fine-tuning de todas as camadas.

| Medida em 145 imagens historicas | SVM distribuido | Novo MobileNetV2 |
| --- | ---: | ---: |
| Acerto da primeira hipotese | 57/145 (39,31%) | 74/145 (51,03%) |
| Acertos aceitos sobre todas as imagens | 31/145 (21,38%) | 51/145 (35,17%) |
| Respostas aceitas, certas ou erradas | 58 | 78 |
| Erros aceitos | 27 | 27 |

O aumento de acertos nao veio acompanhado da reducao dos erros aceitos.
O novo candidato errou as tres fotos de regressao fornecidas pelo usuario;
duas foram aceitas incorretamente como vidro. Portanto, **reprovado para
publicacao**, apesar do ganho agregado. O limiar alto de um escore do modelo
nao garante resposta correta. As tres fotos nao participaram do treinamento.

## Candidato semantico CLIP

Foi ajustada uma cabeca supervisionada sobre caracteristicas CLIP ViT-B/32
QuickGELU, com pesos pre-treinados congelados, usando os mesmos 358 originais
elegiveis. A validacao escolheu C=0,1, mistura de 50% com descricoes semanticas
e limiar 0,8. Os parametros nao foram escolhidos pelas tres fotos do usuario.
CLIP e um Vision Transformer, nao uma rede convolucional. O processamento da
imagem precede ambos os candidatos, com normalizacao especifica de cada rede.

| Medida no teste historico | SVM distribuido | CLIP com base corrigida |
| --- | ---: | ---: |
| Acerto da primeira hipotese | 57/145 (39,31%) | 97/145 (66,90%) |
| Respostas aceitas | 58/145 | 50/145 |
| Acertos entre aceitas | 31/58 (53,45%) | 47/50 (94,00%) |
| Erros aceitos | 27 | 3 |
| Imagens rejeitadas | 87 | 95 |

O ganho da primeira hipotese foi de 27,59 pontos percentuais em relacao ao
SVM distribuido, com menor cobertura. Os 94% descrevem somente as 50 respostas
aceitas, nao todas as imagens. Macro-F1 das seis classes: 61,80%.

Nas fotos de regressao, a hipotese passou a ser correta nas tres imagens:
garrafas PET e lata alta foram aceitas; a lata vermelha ficou abaixo do limiar.
Nao reduzir o limiar com base nesses exemplos para anunciar tres deteccoes.

O experimento CLIP anterior tinha 73,79% de acerto historico, mas usava um
treino com exclusoes menos restritivas. O novo resultado nao supera aquele
experimento e nao autoriza reintroduzir imagens fora do escopo. Pilhas e
eletronicos precisam de mais exemplos revisados. Tambem falta uma avaliacao
nova com negativos e objetos fora do escopo. O banco de descricoes semanticas
herdado ainda menciona alguns itens fora dos 12 objetos definidos; ele nao
comprova atendimento estrito ao escopo por objeto.

**Situacao:** candidato experimental salvo localmente, nao publicado no
Streamlit. Os criterios de liberacao global ainda nao foram satisfeitos.
O arquivo salvo foi recarregado e repetiu as tres hipoteses corretas, com duas
aceitas e nenhuma resposta errada aceita nesses tres casos. A suite executada
apos as mudancas passou com 460 testes, 2 ignorados e 100 subtestes; isso mede
corretude do software, nao acuracia do reconhecimento.

```powershell
tmp/finetune-env/Scripts/python.exe scripts/train_contrastive_probe.py --source reports/recognition_experiment_20261022_input/images --reference-run reports/recognition_experiment_20261022 --cache-dir tmp/clip-weights --output reports/recognition_semantic_20261022 --cases tmp/recognition_cases.csv
tmp/finetune-env/Scripts/python.exe scripts/evaluate_recognition_cases.py --candidate reports/recognition_semantic_20261022 --cases tmp/recognition_cases.csv --cache-dir tmp/clip-weights --output reports/recognition_semantic_20261022/reloaded_cases.json
```

## Reproducao do candidato convolucional

Os dados e modelos permanecem locais; nao sao incluidos no repositorio.

```powershell
python scripts/stage_training_experiment.py --reference reports/scope_corrected_v1/dataset_manifest.json --source ../ecoscan/data/curated --additions data/curated/objects_v1_taco_reviewed/manifest.json --extra-source data/curated/objects_v1_taco_reviewed --output reports/recognition_experiment_20261022_input
python scripts/train_deep_candidate.py --source reports/recognition_experiment_20261022_input/images --groups reports/recognition_experiment_20261022_input/groups.csv --backbone reports/training_reviewed_20261017/mobilenetv2-12.onnx --output reports/recognition_experiment_20261022 --fixed-split reports/scope_corrected_v1/dataset_manifest.json --review-index reports/review_20261017/review_index.csv --review-decisions docs/curation_scope_v1.json --feature-cache reports/training_reviewed_20261017 --augment
python scripts/compare_recognition_candidate.py --candidate reports/recognition_experiment_20261022 --source reports/recognition_experiment_20261022_input/images --cases reports/recognition_regression_cases_20261022.json
```

Use novos diretorios para repetir o experimento. O manifesto local de casos
contem caminhos de fotos e classes esperadas, nao dados de acesso ao sistema.
O script de comparacao rejeita casos com hash ja presente na referencia.

## Disponibilizacao assistida no Streamlit

A exportacao ONNX INT8 foi reprovada: reduziu o acerto para 20% no teste fixo.
Nao usar os arquivos desse experimento no aplicativo. A exportacao FP16,
apos correcao de tipos dos nos Cast, preservou 97/145 hipoteses corretas e
47/50 respostas corretas acima do limiar, com as mesmas tres hipoteses corretas
nas fotos conhecidas. A versao FP16 dispensa PyTorch no servidor.

O pacote `models/semantic-v1` contem partes do encoder, cabeca numerica NPZ,
metadados e licenca. O carregador verifica hashes, reconstrui o encoder e
compartilha uma sessao CPU com dois threads. Nao ha download externo de pesos
na primeira analise nem desserializacao pickle dessa cabeca na aplicacao.

`model.semantic_preview_enabled` ativa a sugestao assistida. Um modelo remoto
aprovado continua tendo prioridade. Na ausencia dele, a tela apresenta a
hipotese sem confirmar material, destino ou pontos de missao automaticamente.
Regras heuristicas de cor/formato nao sobrescrevem as hipoteses desse modelo.
Desativar essa opcao restaura a selecao anterior sem remover arquivos.

A publicacao dessa previa nao equivale a aprovar o candidato para reconhecimento
automatico global. O treinamento automatico de contribuicoes ainda utiliza
o executor SVM e seus criterios; ele nao retreina essa rede semantica.
