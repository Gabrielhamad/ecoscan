# Ampliacao revisada: vidro, papel e papelao

## Objetivo e decisao

Complementar o lote anterior de plasticos e latas com exemplos revisados de
vidro e papel. O treino foi executado, mas **o candidato foi rejeitado**:
nao substitui a cabeca publicada nem a base automatica de treinamento.
Mais imagens nao significam, por si so, reconhecimento melhor.

## Fontes e revisao

- TACO: https://github.com/pedropro/TACO. Foram capturados 30 candidatos de
  papel/papelao, dos quais 19 foram aprovados visualmente. A busca nao encontrou
  novas cenas de vidro elegiveis depois das exclusoes.
- TrashNet: https://github.com/garythung/trashnet e
  https://huggingface.co/datasets/garythung/trashnet. Do arquivo oficial ja
  disponivel localmente, foram separados 48 candidatos e aprovadas 33 imagens
  de garrafas e potes. O arquivo foi conferido por SHA-256.
- Fragmentos, itens ambiguos e imagens com pouca visibilidade foram excluidos.
  A revisao visual foi realizada pelo assistente; nao equivale a uma auditoria
  independente por varios anotadores.
- Os metadados preservam origem, hash, decisao e agrupamento. Nao sao
  redistribuidas fotos neste diretorio. O MIT do repositorio nao deve ser
  presumido como licenca uniforme para todas as imagens do TACO.

## Separacao e processamento

Dos 52 exemplos aprovados, 49 entraram no experimento de treino (33 vidro e
16 papel/papelao) e 3 de papel foram reservados para teste. O conjunto candidato
totalizou 446 exemplos de treino. Imagens de uma mesma cena TACO permanecem
na mesma divisao. O vidro deste lote foi agrupado apenas em treino: nao existe
teste independente novo de vidro, nem garantia de 33 objetos fisicos distintos.

Foram aplicados o mesmo preparo RGB e filtro adaptativo usados na inferencia.
Segmentacao e morfologia nao foram aplicadas como mascara na entrada neural.
O encoder CLIP permaneceu congelado; foi retreinada a cabeca supervisionada,
com os hiperparametros existentes, e nao toda a rede convolucional.

## Resultado medido

| Conjunto | Modelo publicado | Candidato |
|---|---:|---:|
| Validacao historica | 101/145 | 100/145 |
| Macro-F1 de validacao | 0,6510 | 0,6316 |
| Teste historico | 97/145 | 93/145 |
| Novo teste de papel | 3/3 | 3/3 |
| Erros confiantes no teste historico | 3 | 4 |

O conjunto historico ja foi consultado em outros experimentos; nao e uma
estimativa independente final. Tres exemplos novos de papel nao sustentam
uma alegacao de precisao geral. As metricas descrevem a primeira classe
predita; nao dispensam a confirmacao exigida pela interface.

## Proximos criterios

1. Ampliar e revisar pilhas e os tipos de eletronicos definidos no escopo.
2. Formar uma avaliacao nova com fotos reais de celular e objetos distintos,
   preservada antes do treinamento e separada por objeto/cena.
3. Investigar a regressao sem ajustar parametros usando o teste historico.
4. Publicar somente com melhoria na validacao, sem regressao por material
   e sem aumento de erros confiantes.

Artefatos locais do experimento: `reports/balance_training_20261023/`.
O arquivo `evaluation.json` registra as metricas; `provenance.json` registra
as imagens revisadas sem incluir seus bytes.
