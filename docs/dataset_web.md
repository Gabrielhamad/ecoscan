# Imagens publicas para treinamento

## Fonte incorporada

TrashNet, de Gary Thung e Mindy Yang, publicado pelos autores no
[GitHub](https://github.com/garythung/trashnet) e no
[Hugging Face](https://huggingface.co/datasets/garythung/trashnet).
A ficha do dataset declara licenca MIT; o importador preserva a licenca completa
em `TRASHNET_LICENSE` junto aos dados. O README dos autores solicita citacao.

Foi utilizado o arquivo oficial `dataset-resized.zip` (aproximadamente 42,8 MB).
SHA-256 verificado:
`c060e8abfe5d6de0578ca15be1ed8ad0794a865d333c3473d53d1d9ad6e38b8c`.
O importador interrompe se o arquivo futuro tiver outro hash.

As fotos retratam objetos sobre fundo claro, capturados com celulares. Isso
amplia exemplos de materiais mas nao cobre sozinho fundos complexos, multiplos
residuos ou todos os estados de conservacao. Os rotulos vieram dos autores;
houve verificacao automatica de arquivos e inspecao visual de amostras, sem
afirmar revisao humana de cada foto.

## Mapeamento para o EcoScan

| TrashNet | EcoScan |
| --- | --- |
| metal | metal |
| plastic | plastic |
| glass | glass |
| paper e cardboard | paper_cardboard |
| trash | Nao importado, fora do escopo definido |

Esta fonte nao amplia pilhas ou eletronicos. Essas classes permanecem com os
exemplos existentes nesta rodada; nao foram representadas como cobertas pela
base nova. Oleo, medicamentos e organicos nao foram adicionados ao treinamento.

## Importacao realizada

Foram mantidos os 723 originais da referencia e importadas 2358 fotos novas:
979 de papel/papelao, 496 de vidro, 408 de metal e 475 de plastico. Foram
excluidas 32 candidatas pelo filtro de copia exata ou proximidade de dHash.
Esse filtro e conservador: algumas imagens parecidas podem ser objetos
distintos. Nao houve exclusao das fotos originais do projeto.

`web_provenance.json` registra URL, autores, licenca, hash do ZIP, hash da
referencia, arquivo original no ZIP, classe de origem, hash de cada imagem e
rejeicoes. Os arquivos sao preservados sem retoque manual. O preparo RGB
adaptativo e aplicado pelo treinamento antes da extracao neural, com decisao
de filtragem registrada no manifesto da rodada.

## Avaliacao preservada

O comando `--fixed-split` conserva caminhos, hashes, classes e splits de todas
as fotos da referencia. As novas fotos entram exclusivamente no treino.
Nao se aumenta artificialmente o teste com fotos faceis da nova base.
Reagrupamento que conecte treino e avaliacao interrompe o processo, assim como
uma foto adicional proxima de um grupo reservado. Copias visuais sao filtradas
antes da importacao, mas dHash nao prova independencia de objetos fisicos.

O conjunto resultante contem 3081 imagens: 2791 no treino, 145 na validacao e
145 no teste. O teste anterior ja foi usado em comparacoes e e exploratorio;
sera necessario outro lote de objetos para o aceite final.

O cache anterior de caracteristicas pode ser reutilizado apesar da nova pasta
de origem somente no modo de referencia fixa: identificador do arquivo, hash,
classe, processamento, representacao e backbone continuam verificados.
Os pesos anteriores, originais e cache de origem permanecem intactos.

## Comparacao de origens

O sinalizador `--balance-source` compara a mistura completa com o treino de
referencia e duas misturas ponderadas. Nas misturas, cada classe tem a mesma
massa total e a contribuicao externa por classe equivale a 25% ou 100% da
contribuicao de referencia. Classes sem fotos externas continuam representadas.
Tanto StandardScaler quanto regressao logistica recebem os pesos; a ponderacao
nao e aplicada duas vezes pelo `class_weight`. O total de pesos preserva o
tamanho efetivo da referencia para comparar as regularizacoes.

Esse modo requer referencia fixa e nao combina com ampliacao sintetica. Ele
nao usa os erros do teste para escolher os pesos: as duas proporcoes sao
comparadas somente na validacao. A selecao pode escolher `reference_only`;
nesse caso, as novas fotos foram usadas nos candidatos experimentais, mas nao
no modelo selecionado. `fit_sample_count` explicita a quantidade efetiva de
amostras do candidato escolhido nas futuras rodadas.

## Reproduzir

Na raiz do repositorio, com a rodada de referencia local disponivel:

```powershell
python scripts/import_trashnet.py --source ../ecoscan/data/curated --reference reports/training_embedding_20261016/dataset_manifest.json --download-dir data/raw/trashnet_20261017 --output data/curated/web_20261017
python scripts/train_deep_candidate.py --source data/curated/web_20261017 --backbone tmp/mobilenetv2-12.onnx --output reports/training_web_20261017 --feature-cache reports/training_embedding_20261016 --fixed-split reports/training_embedding_20261016/dataset_manifest.json --heads compare
python scripts/train_deep_candidate.py --source data/curated/web_20261017 --backbone tmp/mobilenetv2-12.onnx --output reports/training_web_balanced_20261017 --feature-cache reports/training_web_20261017 --fixed-split reports/training_embedding_20261016/dataset_manifest.json --balance-source
```

Para novos experimentos, escolher diretorios de saida novos. O importador baixa
apenas arquivos das fontes oficiais indicadas; nao usa resultados de busca como
rotulos. O ZIP nao e extraido indiscriminadamente: somente imagens de classes
e caminhos previstos sao lidas. Imagens, ZIP, manifesto completo e modelos ficam
locais em diretorios ignorados pelo Git. Codigo e documentacao podem ser
compartilhados sem publicar fotos pessoais da referencia.

Ver [resultados medidos nesta rodada](resultado_dataset_web_20261017.md).
