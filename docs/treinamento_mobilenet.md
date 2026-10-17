# Treinamento com representacoes MobileNetV2

O novo ciclo usa uma rede MobileNetV2 pre-treinada no ImageNet, executada no
OpenCV DNN. O padrao agora extrai 1280 caracteristicas internas, antes da camada
de classificacao ImageNet (`--representation embedding`). O modo anterior de
1000 logits continua disponivel com `--representation logits`; os dois formatos
tem metadados e caches separados. Uma regressao logistica
supervisionada aprende as seis classes do EcoScan, com pesos balanceados.
Nao e fine-tuning da rede nem deteccao de objetos por caixas.

## Preparacao compativel

As imagens originais passam pelo preparo RGB `rgb-preserved-v2`: orientacao,
reducao proporcional, filtro adaptativo e letterbox 224x224. A normalizacao
ImageNet ocorre uma vez, imediatamente antes da rede. As cores nao sao
substituidas por mascaras binarias. Segmentacao e mapas continuam disponiveis
na analise do aplicativo; o lote dispensa esses diagnosticos porque eles nao
alteram a entrada do classificador. Um teste compara os pixels dos dois modos.

## Dados e separacao

Usar somente pastas curadas das classes `plastic`, `paper_cardboard`, `metal`,
`glass`, `battery`, `electronic`. Oleo e medicamentos permanecem educativos.
Nao importar fotos de usuarios sem consentimento e aprovacao do analista.
O treinamento nao executa download de contribuicoes privadas automaticamente.

O manifesto registra arquivo, classe, SHA-256 original e dos pixels, dHash,
grupo, filtro aplicado, qualidade e split. Copias identicas com rotulos
conflitantes interrompem a rodada. Copias exatas, proximas por dHash e grupos
de captura declarados ficam no mesmo conjunto. Cinco folds estratificados
por grupo produzem aproximadamente 60% treino, 20% validacao e 20% teste.
Cada classe precisa estar presente nos tres conjuntos.

O dHash nao identifica necessariamente o mesmo objeto fotografado de outro
angulo. Para uma avaliacao mais forte, fornecer um CSV completo:

```csv
path,group_id
metal/lata_frente.jpg,lata_001_sessao_01
metal/lata_lateral.jpg,lata_001_sessao_01
plastic/garrafa_amassada.jpg,garrafa_002_sessao_02
```

Todas as fotos do mesmo objeto devem compartilhar o grupo, inclusive em dias
ou fundos diferentes. O CSV deve cobrir todas as imagens selecionadas. As
variacoes sinteticas futuras devem manter o grupo da foto original e ser
aplicadas apenas depois da divisao, somente ao treino.

## Executar em CPU

Nao exige TensorFlow, PyTorch, GPU ou servico pago. Usa as dependencias existentes.
Baixar o arquivo oficial ONNX indicado abaixo; o script confere o hash antes de
carregar a rede. Executar a partir da raiz do repositorio:

```powershell
python scripts/train_deep_candidate.py --source data/curated --backbone CAMINHO/mobilenetv2-12.onnx --output reports/treino_001 --groups data/capture_groups.csv
```

Sem CSV, omitir `--groups`; o relatorio registra essa limitacao. O destino deve
ser novo e separado das imagens e dos modelos ativos. Para retomar uma rodada:

```powershell
python scripts/train_deep_candidate.py --source data/curated --backbone CAMINHO/mobilenetv2-12.onnx --output reports/treino_001 --resume
```

Checkpoints por foto verificam o hash dos dados, das caracteristicas, do
processamento e da rede. Alterar a rede, preparo ou baseline exige nova rodada.
Novas fotos ou alteracoes de grupo recalculam o split; nao tratar essa nova
rodada como comparacao com teste congelado anterior.

O nome da representacao tambem integra o cache. Diretorios de rodadas antigas
sem esse campo devem ser preservados; iniciar um novo diretorio para treinar.

## Casos reais e evolucao

Manter um CSV `path,expected_class` com fotos revisadas que ja provocaram erros.
Os caminhos podem ser relativos ao CSV. Executar o preparo completo antes de
classificar, registrando as tecnicas e decisoes de cada imagem:

```powershell
python scripts/evaluate_recognition_cases.py --candidate reports/treino_001 --cases data/casos_reais.csv --output reports/casos_001.json
```

O relatorio registra acertos, rejeicoes e erros aceitos, junto ao hash do modelo
e das fotos. Esses casos sao regressoes conhecidas; depois de usa-los para orientar
melhorias, reservar outras fotos para estimar o desempenho real. Repetir medidas
no mesmo teste para escolher arquiteturas tambem torna esse teste exploratorio.

Para aumentar a utilidade: revisar rotulos e objeto principal; reunir variacoes
de latas, PET, vidro, papel, pilhas e eletronicos; agrupar fotos do mesmo objeto;
avaliar deteccao de objetos com caixas anotadas quando houver varios residuos.
O extrator atual classifica a imagem inteira e nao fornece caixas semanticas.
Comparar futuramente fine-tuning e recortes de objetos em um protocolo separado.
Filtros devem preservar evidencias: aplicar mais suavizacao nao garante acerto.
Um mapa de segmentacao mostra regioes visuais, nao comprova por si so o material.

## Selecao e avaliacao

### Variacoes de captura somente no treino

Opcao `--augment`: compara o treino original com uma versao ampliada por tres
variacoes deterministicas: exposicao mais escura, mais clara e inclinacao de
7 graus com canvas expandido para evitar cortar o objeto. Cada variacao passa
pelo preparo adaptativo do aplicativo antes da extracao neural. A reducao de
trabalho proporcional ocorre antes de gerar as variacoes, evitando arquivos
temporarios desnecessariamente grandes. As imagens originais sao preservadas.

```powershell
python scripts/train_deep_candidate.py --source data/curated --backbone CAMINHO/mobilenetv2-12.onnx --output reports/treino_variacoes --augment --feature-cache reports/treino_anterior
```

`--feature-cache` e opcional e reutiliza apenas caracteristicas originais com
hash verificado e perfil identico. Um cache de logits nao pode alimentar um
treino de embeddings. O cache anterior permanece intacto.

As variacoes sao geradas depois da divisao por grupos, exclusivamente para
os pais no treino. `augmentation_manifest.json` registra origem, SHA-256,
grupo, tecnica, versao e filtragem. Validacao e teste conservam suas imagens
originais. O manifesto de originais nao inclui as variacoes como novos objetos.
As variacoes sao recomputadas em uma retomada; nao possuem cache persistente.

O script compara as tres regularizacoes com e sem variacoes pela validacao;
se a ampliacao piorar o macro-F1, a versao original pode vencer. Nao ajustar
parametros pelo resultado das fotos conhecidas ou do teste exploratorio.
Variacoes sinteticas nao substituem fotos de novos objetos, fundos e angulos.

Tres regularizacoes da regressao logistica sao comparadas pelo macro-F1 da
validacao. O teste nao escolhe parametros. A politica de rejeicao busca 90%
de acerto em pelo menos 20 respostas aceitas na validacao; quando isso nao
acontece, usa limiar conservador de 0,95, sem declarar a meta atingida.

`training_summary.json` apresenta precisao, recall e F1 por classe, matriz de
confusao, acuracia total, cobertura e acerto entre respostas aceitas. Avaliar
essas medidas juntas: rejeitar quase tudo nao torna o sistema util. Os escores
da regressao nao foram calibrados como probabilidade de descarte correto.
`test_predictions.csv` identifica erros para revisao.

A comparacao com o modelo antigo utiliza os mesmos pixels preparados. Esse
modelo pode ter visto as imagens em rodadas anteriores; portanto, essa
comparacao e diagnostica e nao prova um ganho independente em campo.

## Artefatos e publicacao

O diretorio da rodada contem `candidate.joblib`, backbone ONNX, contrato de
processamento, manifesto, metricas, predicoes e checkpoints. Pesos MobileNet
sao verificados pelo SHA-256
`c0c3f76d93fa3fd6580652a45618618a220fced18babf65774ed169de0432ad5`.
O carregador local valida classes, integridade e contrato antes da inferencia.
Carregar joblib apenas de artefatos confiaveis produzidos pela equipe.

O treino nao altera o reconhecimento publicado. Para promover: revisar erros,
avaliar fotos novas do grupo fora do treino (latas e garrafas amassadas, caixas
dobradas, luz/fundos variados), medir tempo de resposta no servidor e integrar
explicitamente o novo bundle. Ate isso ocorrer, o app continua com o modelo
anterior. Reportes aprovados alimentam uma proxima rodada supervisionada;
nao existe aprendizado instantaneo por clicar em reportar.

Fontes tecnicas:
[ONNX Model Zoo e normalizacao](https://github.com/onnx/models/blob/main/validated/vision/classification/mobilenet/README.md),
[pesos oficiais](https://github.com/onnx/models/blob/main/validated/vision/classification/mobilenet/model/mobilenetv2-12.onnx),
[MobileNetV2](https://arxiv.org/abs/1801.04381).
