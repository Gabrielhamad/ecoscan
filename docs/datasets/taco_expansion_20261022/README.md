# Expansao revisada com imagens da internet

## Origem

Fonte: [TACO oficial](https://github.com/pedropro/TACO), anotacoes oficiais COCO.
O [artigo dos autores](https://arxiv.org/html/2003.06975v2), secao II, informa que
as imagens possuem licencas livres e descreve a anotacao manual. O campo de licenca
individual esta ausente em parte dos metadados: nao assumimos que a licenca MIT do
codigo equivale a uma licenca uniforme para todas as fotos. Imagens nao foram
redistribuidas no GitHub. URLs de origem, anotacoes, hashes e decisoes de revisao
ficam em `provenance.json` e `review.json`.

## Selecao

- 75 imagens capturadas: 50 plasticos e 25 latas. O filtro de tamanho e a exclusao
  de cenas anteriores impediram atingir a meta inicial de 50 latas nesta fonte.
- Revisao visual de todas as 75: 55 aprovadas e 20 rejeitadas.
- Aprovadas: 29 garrafas PET, 5 recipientes plasticos, 19 latas de bebida e 2 de conserva.
- Exclusoes: embalagens quimicas, galoes de combustivel, fragmentos e casos ambiguos.
- Duplicatas exatas/perceptuais e cenas conhecidas foram verificadas contra a base anterior.
- Separacao deterministica por cena antes do ajuste: 39 imagens de treino e 16 de teste.
- Treino acrescentado: 25 plasticos e 14 latas; teste novo: 9 plasticos e 7 latas.

## Treinamento e resultados

Mesmo preparo RGB adaptativo do aplicativo, encoder CLIP ONNX congelado e ajuste
da cabeca logistica com C=0,1 e pesos balanceados. Nenhuma nova busca de parametros
foi realizada usando o teste. Filtros efetivamente aplicados constam no manifesto.

| Avaliacao | Modelo anterior | Candidato |
|---|---:|---:|
| Teste de cenas novas (16 recortes) | 13/16 | 15/16 |
| Validacao historica (145 imagens) | 101/145 | 96/145 |
| Teste historico (145 imagens) | 97/145 | 96/145 |

No teste novo: plasticos passaram de 8/9 para 9/9; latas passaram de 5/7 para 6/7.
Isso e uma melhoria localizada em uma amostra pequena, nao uma precisao global de
93,75%. A validacao geral piorou; o candidato NAO substituiu o modelo publicado.
Resultados completos em `evaluation.json`.

## Integracao com aprendizado automatico

A base de caracteristicas de treino passou de 358 para 397 imagens, sem incorporar
as 16 imagens novas de teste. A validacao fixa permanece com 145 exemplos.
O executor detecta alteracoes no hash da base e reavalia contribuicoes aprovadas
mesmo quando o lote anterior nao foi promovido. Nao repete um lote concluido
enquanto a base e as revisoes permanecerem iguais.

## Limites

Esta rodada nao ampliou pilhas ou eletronicos. Recortes anotados nao substituem
testes com enquadramentos completos de celular. Separacao por cena e hash perceptual
reduzem vazamentos, mas nao provam que objetos fisicos diferentes foram fotografados.
Validacao e teste historicos ja foram consultados em experimentos anteriores.
Revisao visual do assistente nao certifica composicao quimica ou ausencia de residuos.
