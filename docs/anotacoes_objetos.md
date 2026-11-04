# Anotacoes de objetos para avaliacao e deteccao

O manifesto separa `object_type` (por exemplo, garrafa) de `material` (vidro,
plastico etc.). O material precisa de evidencia ou revisao; nao e deduzido
automaticamente pelo nome do objeto. `unknown` registra composicao incerta.

## Estrutura

`schema_version: 1` e uma lista `images`. Cada imagem registra:

- `image_id`, `file_name` relativo a uma raiz e SHA-256 do original.
- `oriented_size: [largura, altura]` depois da orientacao EXIF.
- `group_id` para o mesmo objeto/sessao e `split`: train, validation, test ou regression.
- `annotation_status`: proposal ou verified; verified exige `reviewed_by`.
- `objects`: ID, tipo de objeto, material, origem da informacao, kind e caixa.

A caixa `box_xyxy_normalized` usa `[esquerda, topo, direita, base]` entre 0 e 1.
`kind` distingue um objeto individual (`single`) de um grupo (`group`). A
origem do material pode ser user_report, dataset_publisher, analyst_verified
ou unknown. Propostas nao sao aprovadas automaticamente para treino.

O carregador verifica arquivos, hashes, dimensoes orientadas, caixas finitas,
IDs unicos e ausencia de imagens/grupos atravessando splits. Manter um manifesto
mestre com todos os splits: registros separados nao substituem um catalogo
global. Copias exatas duplicadas tambem sao rejeitadas para nao inflar contagens.
Fotos de outro angulo do mesmo objeto exigem o mesmo group_id, informado pela equipe.

## Exportar caixas COCO

O comando abaixo exige anotacoes verificadas e individuais, de material conhecido.
Regressoes e grupos nao podem ser exportados como objetos de treino. Imagens
sem objetos, quando revisadas, podem representar negativos.

```bash
python scripts/evaluate_object_annotations.py --annotations CAMINHO/manifesto.json --source-root CAMINHO/imagens --output reports/objetos_exportados --export-coco train
```

A exportacao grava `instances.json` com caixas em pixels `[x,y,largura,altura]`
e imagens PNG RGB orientadas pelo EXIF. Os originais sao preservados. Isso
evita caixas calculadas na foto em pe ficarem desalinhadas com o JPEG deitado.
E uma exportacao de bounding boxes, nao de mascaras de segmentacao.
O campo reviewed_by e rastreabilidade local, nao uma autenticacao de analista
nem integracao ja disponivel na interface da secretaria.

## Proximo lote

Reunir objetos distintos das seis categorias, imagens negativas e cenas reais.
Anotar o alvo principal, estado, material e grupo de captura. Reservar objetos
inteiros antes de treinar; nao reutilizar as tres regressoes como novo teste cego.
So depois comparar detectores com caixas revisadas e avaliar localizacao e
classificacao separadamente.
