# Pesquisa web de datasets e captura inicial

## Objetivo

Encontrar fontes viáveis para montar o dataset do EcoScan sem depender de API paga nem de serviços externos durante a execução da aplicação.

## Fontes pesquisadas

### TACO

TACO: Trash Annotations in Context é um dataset aberto de resíduos em ambientes reais, com anotações de segmentação e detecção em formato COCO. É forte para demonstrar segmentação e detecção futura, mas não cobre diretamente todas as classes do EcoScan como classes simples de classificação.

Uso implementado: `scripts/capture_taco_dataset.py` baixa imagens necessárias, recorta os objetos anotados e reforça classes como `medicine` e `aerosol` sem usar a cena inteira como rótulo.

Fonte: https://github.com/pedropro/TACO

### Dataset Ninja / TACO

O espelho documenta TACO com licença CC BY 4.0, 1500 imagens, 9823 objetos e 60 classes. É útil para relatório, visualização da taxonomia e comparação com datasets de segmentação.

Fonte: https://datasetninja.com/taco

### Merged Waste Classification Dataset

MWCD foi publicado em 14 de agosto de 2026 no Mendeley Data, com licença CC BY 4.0. Possui 35168 imagens RGB em nove categorias: battery, cardboard, glass, metal, organic, paper, plastic, textile e trash.

Uso recomendado: candidato forte para o treinamento final porque cobre quase todas as classes atuais. Falta separar explicitamente eletrônico/e-waste.

Fonte: https://data.mendeley.com/datasets/x863v66fv3/1

### NexTech14 Waste Dataset

Dataset com 11 categorias, incluindo battery, e-waste, food-waste, garden-waste, other-organic-waste, glass, metal, paper, plastic, textile-fabric e general trash.

Uso recomendado: candidato forte para complementar eletrônico e orgânico, sujeito a download, revisão de licença e padronização de labels.

Fonte: https://data.mendeley.com/datasets/p6hgv27jh4/1

### TrashBusters Combined

Dataset harmonizado no Hugging Face com seis classes: cardboard, glass, metal, paper, plastic e trash. A página indica licença MIT e combina várias fontes públicas.

Uso recomendado: bom para recicláveis tradicionais, mas não cobre pilha/bateria, orgânico e eletrônico.

Fonte: https://huggingface.co/datasets/TrashBusters/combined

### Kaggle Garbage Dataset PlusYaml

Dataset descrito com classes paper, plastic, glass, metal, organic, electronics e miscellaneous, licença CC0 e estrutura YOLO. A limitação prática é exigir acesso/autenticação Kaggle para download automatizado.

Uso recomendado: ótimo candidato se o grupo tiver conta Kaggle e quiser incluir eletrônicos. Requer validação manual e conversão para classificação de imagem única.

Fonte: https://www.kaggle.com/datasets/engrbasit62/garbage-dataset-plusyaml

### Wikimedia Commons

Wikimedia Commons permite buscar arquivos por categoria via MediaWiki API e recuperar metadados de licença por arquivo com `prop=imageinfo` e `iiprop=extmetadata`.

Uso recomendado: captura inicial controlada para desenvolver e demonstrar o pipeline enquanto o dataset final é escolhido.

Fontes:

- https://commons.wikimedia.org/wiki/Category:Plastic_bottles
- https://commons.wikimedia.org/wiki/Category:Cardboard_boxes
- https://commons.wikimedia.org/wiki/Category:Aluminium_cans
- https://commons.wikimedia.org/wiki/Category:Glass_bottles
- https://commons.wikimedia.org/wiki/Category:Food_waste
- https://commons.wikimedia.org/wiki/Category:Electric_batteries
- https://commons.wikimedia.org/wiki/Category:Electronic_waste
- https://commons.wikimedia.org/wiki/Commons:API/MediaWiki
- https://commons.wikimedia.org/wiki/Help:Machine-readable_data

## Decisão para a captura inicial

A captura inicial do EcoScan usa Wikimedia Commons porque:

- não exige login;
- cobre as sete classes atuais;
- permite salvar metadados de autoria e licença;
- gera uma base pequena suficiente para testar aquisição, validação, filtros, segmentação e interface;
- não deve ser confundida com dataset final de treinamento.

Após a primeira captura, as categorias do arquivo `config/web_image_sources.json` foram refinadas para priorizar fontes mais específicas nas próximas coletas, como `Disposable AA batteries`, `AA batteries`, `Banana peel`, `Spoiled food`, `Plastic bottles as waste`, `Paper recycling` e `Printed circuit board assemblies`.

## Limitações da captura inicial

- Categorias do Commons podem conter imagens com contexto complexo ou múltiplos objetos.
- Algumas imagens representam o material, não necessariamente o resíduo descartado.
- Orgânico e eletrônico exigem revisão visual cuidadosa.
- O dataset capturado é semente de desenvolvimento; o modelo final ainda deve usar dataset maior, revisado e dividido corretamente.

## Procedimento implementado

O script `scripts/capture_wikimedia_dataset.py`:

1. lê `config/web_image_sources.json`;
2. consulta arquivos por categoria no Wikimedia Commons;
3. baixa miniaturas em JPG/PNG;
4. organiza em `data/raw/<classe>`;
5. salva manifesto de atribuição em `reports/web_capture`;
6. preserva licença, URL, autor/crédito e hash SHA-256 quando disponíveis.

O script `scripts/capture_taco_dataset.py`:

1. lê `config/taco_category_map.json`;
2. baixa as anotações COCO do TACO;
3. mapeia categorias TACO para classes EcoScan;
4. baixa somente as imagens necessárias;
5. recorta o objeto anotado por bounding box;
6. salva os recortes em `data/raw/<classe>`;
7. grava manifesto em `reports/taco_capture`.
