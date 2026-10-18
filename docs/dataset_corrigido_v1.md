# Correcao e ampliacao do dataset por objeto

## Resultado executado

- 88 exemplos antigos de treino revisados novamente nas classes pilhas e
  eletronicos. Apenas 2 exemplos claros de AA/AAA e 1 celular foram mantidos
  nesse subconjunto; os demais ficaram excluidos ou pendentes de revisao.
- 98 exclusoes acumuladas no manifesto corrigido, incluindo as decisoes
  anteriores. Nenhuma imagem original foi apagada ou relabelada automaticamente.
- Validacao e teste antigos preservados integralmente.
- 36 recortes de cenas TACO ausentes da referencia reconstruidos com EXIF.
- 23 novos exemplos aprovados visualmente e exportados como treino;
  13 excluidos da exportacao. Nenhum desses exemplos foi usado em novo treino
  ou para anunciar aumento de acuracia nesta etapa.

| Objeto | Novos exemplos revisados |
| --- | ---: |
| Garrafa PET | 9 |
| Lata de bebida | 7 |
| Folha de papel | 6 |
| Caixa de papelao | 1 |

Nao foi possivel obter novas cenas de vidro na selecao restrita desta coleta;
as cenas disponiveis ja constavam na referencia. TACO nao supriu pilhas AA/AAA
nem os tres eletronicos definidos. Os demais oito tipos de objeto nao receberam
novos exemplos aprovados nesta rodada.

## Falha corrigida no importador

Algumas fotos continham rotacao EXIF. O importador convertia RGB sem aplicar
essa orientacao antes do recorte. Coordenadas para a imagem orientada podiam
recortar o chao em vez do objeto. Agora a orientacao e aplicada primeiro e a
proporcao e comparada com a anotacao; incompatibilidades sao rejeitadas.
O defeito foi reproduzido e coberto por teste com EXIF 6.

Recortes antigos de qualquer importacao TACO precisam de auditoria; nao basta
trocar o modelo e continuar usando as mesmas imagens mal recortadas. A revisao
atual nao certifica que todos os recortes antigos foram corrigidos.

## Artefatos locais

- `reports/scope_corrected_v1/dataset_manifest.json`: manifesto antigo com a
  elegibilidade corrigida. Ainda contem materiais comuns sem revisao por objeto.
- `data/curated/objects_v1_taco_reviewed/`: 23 PNGs, manifesto com objeto,
  material, origem, hash e grupo da cena, decisoes e anotacoes da fonte.
- `data/raw/taco_scope_rebuilt_v1/`: recortes reconstruidos e fontes preservadas.
- `docs/curation_scope_v1.json`: decisoes das classes antigas, vinculadas ao indice.
- `docs/taco_scope_review_v1.json`: decisoes do novo lote, vinculadas a captura.
- `docs/datasets/taco_v1/`: metadados da coleta para o grupo reproduzir.

As fotos locais nao sao automaticamente publicadas no Streamlit. O aplicativo
nao foi retreinado nesta etapa. A revisao foi visual pelo assistente, sem
certificacao de material ou confirmacao do conteudo das embalagens.

## Integridade e separacao

O exportador exclui cenas TACO presentes em qualquer split da referencia e
compara identidades RGB e dHash com todos os exemplos antigos. Recortes da mesma
cena nova compartilham grupo. dHash e uma heuristica e pode rejeitar imagens
distintas; cenas diferentes tambem podem retratar o mesmo objeto fisico.
Portanto isso nao comprova um teste independente por objeto.

Os proximos exemplos devem priorizar AA/AAA, celular, mouse, carregador,
frasco/pote rigido, lata de conserva vazia e pote/garrafa de vidro. Cada exemplo
precisa de objeto identificado e sessao registrada. Nao completar essas lacunas
com monitores, placas, baterias industriais ou fragmentos sem identidade.

## Reproducao da correcao antiga

```powershell
python scripts/apply_scope_review.py --manifest reports/training_curated_20261017/dataset_manifest.json --index reports/review_20261017/review_index.csv --decisions docs/curation_scope_v1.json --source ../ecoscan/data/curated --output reports/nova_revisao_scope
```

O treino futuro deve consumir as exclusoes e os grupos de origem. Uma pasta
com fotos adicionais, sem esses metadados, nao substitui o manifesto revisado.

Fontes: [TACO](https://github.com/pedropro/TACO),
[artigo do dataset](https://arxiv.org/abs/2003.06975).
