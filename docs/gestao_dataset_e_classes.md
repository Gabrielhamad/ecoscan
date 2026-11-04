# Gestão do dataset

## Classes atuais

`plastic`, `paper_cardboard`, `metal`, `glass`, `battery` e `electronic`.

Metal, plástico e vidro têm prioridade de coleta. O escopo detalhado está em [Escopo e variações](escopo_e_variacoes.md).

## Fluxo

1. Receber imagem própria consentida ou fonte aberta documentada.
2. Salvar em `data/raw/<classe>` com manifesto e hash.
3. Revisar qualidade, classe, objeto, cena e duplicatas.
4. Promover somente imagens aceitas para `data/curated`.
5. Separar treino, validação e teste por objeto/cena.
6. Preparar RGB com o mesmo contrato da inferência.
7. Ajustar a cabeça candidata sem tocar no teste.
8. Comparar candidato e referência nos mesmos gates.
9. Publicar metadados, hashes, métricas e rollback.

Contribuição aprovada, treino concluído e release publicada são estados distintos. Nenhuma aprovação isolada modifica o modelo ativo.
