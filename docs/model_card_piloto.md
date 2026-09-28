# Cartão do modelo visual do piloto

Este arquivo acompanha o artefato `models/vision_svm_classifier.joblib` quando
ele estiver publicado. Ele é um modelo visual clássico de operação inicial,
não um modelo final de produção.

## Escopo

- Classes: `plastic`, `paper_cardboard`, `metal`, `glass`, `battery`, `electronic`.
- Descritores: RGB/HSV, HOG e LBP sobre a imagem preparada pelo pipeline.
- Classificador: ensemble visual supervisionado selecionado pelo script SVM.
- Limiar de aceitação do artefato: `0.25`; a decisão pública ainda passa por
  verificação de segurança e pode pedir confirmação.
- Regras visuais adicionais: validações conservadoras para garrafas plásticas
  em grupo e latas com geometria/indícios metálicos.

## Resultado da rodada disponível

Na rodada local de 27/09/2026, com 723 imagens curadas, 672 passaram pela
preparação automática e foram divididas em treino, validação e teste. O
candidato selecionado apresentou:

| Conjunto | Acurácia top-1 | Macro-F1 | Observação |
| --- | ---: | ---: | --- |
| Validação | 40,0% | 39,1% | usado para selecionar o candidato |
| Teste independente da rodada | 27,5% | 28,7% | ainda insuficiente para chamar de modelo final |

O limiar de 0,25 aumenta a rejeição de casos ambíguos, mas não corrige uma base
com confusão entre classes. A taxa de abstenção precisa ser lida junto com a
precisão das respostas aceitas; ela não é uma melhoria artificial de acurácia.

## Decisão de uso

O modelo pode apoiar um piloto orientativo, com confirmação do usuário e
reporte de erros. Ele não deve ser usado como única autoridade para descarte
perigoso, nem como evidência de acurácia final. Nenhum candidato deve ser
promovido sem novas fotos independentes, especialmente de latas amassadas,
garrafas deformadas, papéis dobrados, vidro em diferentes estados, pilhas e
eletrônicos com cabos.

O artefato deve ser substituído apenas por uma rodada com manifesto, matriz de
confusão, métricas por classe, revisão humana e aceite em celulares reais.
