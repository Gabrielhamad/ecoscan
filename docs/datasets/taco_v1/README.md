# Evidencias da coleta TACO

Os JSONs desta pasta preservam as propostas de captura, configuracao e anotacoes
da fonte usadas na revisao. As fotos nao estao embutidas no aplicativo nem neste
diretorio. As decisoes estao em `docs/taco_scope_review_v1.json`.

Fonte: https://github.com/pedropro/TACO

Proenca, Pedro F.; Simoes, Pedro. TACO: Trash Annotations in Context for Litter
Detection. 2020. https://arxiv.org/abs/2003.06975

Licenca declarada da base: CC BY 4.0,
https://creativecommons.org/licenses/by/4.0/ . As anotacoes desta versao nao
preenchem licencas individuais das fotos; os URLs de origem foram preservados.
Nao inferir autoria individual ou uma licenca especifica do Flickr sem verificar.

Os recortes revisados sao derivados: orientacao EXIF aplicada antes das
coordenadas, margem de 12%, conversao RGB e PNG sem nova perda de compressao.
Esses recortes ainda precisam do preparo de inferencia antes de treinar.

Para reconstruir localmente a coleta proposta, em um checkout com as
dependencias instaladas:

```powershell
python scripts/repair_taco_crops.py --capture docs/datasets/taco_v1/taco_capture_manifest.json --output data/raw/taco_scope_rebuilt_v1
```

O destino deve ser novo. O comando baixa as fontes e preserva os bytes originais.
Depois, gerar as pranchas com `scripts/review_scope_dataset.py`. A exportacao
exige o manifesto da referencia e as imagens originais locais para procurar
duplicatas. Se os bytes ou hashes mudarem, revisar e vincular novamente as
decisoes; nao desativar a verificacao de integridade.
