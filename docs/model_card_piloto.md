# Cartão do modelo visual do piloto

Este arquivo acompanha o artefato `models/vision_svm_classifier.joblib` quando
ele estiver publicado. Ele é um modelo visual clássico de operação inicial,
não um modelo final de produção.

> **Atualização de 29/09/2026:** a preparação passou para `rgb-preserved-v2`.
> Este artefato não foi retreinado e não possui contrato compatível. Suas
> hipóteses permanecem não confirmadas no app. As métricas abaixo pertencem
> à preparação anterior e não validam a nova. Consulte a
> [revisão de processamento](processamento_preservado_v2.md).

## Escopo

- Classes: `plastic`, `paper_cardboard`, `metal`, `glass`, `battery`, `electronic`.
- Descritores: RGB/HSV, HOG e LBP sobre a imagem preparada pelo pipeline.
- Classificador selecionado: Random Forest visual supervisionado. O nome do
  arquivo contém `svm` por compatibilidade histórica; não descreve o algoritmo.
- Limiar de aceitação do artefato: `0.25`; a decisão pública ainda passa por
  verificação de segurança e pode pedir confirmação.
- Regras visuais adicionais: validações conservadoras para garrafas plásticas
  em grupo e latas com geometria/indícios metálicos.

## Resultado da rodada disponível

Na rodada local de 28/09/2026, com 723 imagens curadas, 672 passaram pela
preparação automática e foram divididas por arquivo em treino, validação e
teste. O candidato selecionado apresentou:

| Conjunto | Acurácia top-1 | Macro-F1 | Observação |
| --- | ---: | ---: | --- |
| Validação | 40,0% | 39,1% | usado para selecionar o candidato |
| Teste separado da rodada | 27,5% | 28,7% | ainda insuficiente para chamar de modelo final |

O split mantém duplicatas exatas juntas, mas **não isola necessariamente o mesmo
objeto, cena ou sessão de captura**. Portanto, esta não é uma estimativa
independente de desempenho em campo. No teste, 68 de 102 imagens ficaram sem
rótulo aceito com limiar de 0,25. Precisão entre respostas aceitas e cobertura
devem ser avaliadas separadamente.

O processamento padrão da aplicação e do preparo do dataset foi alinhado para
filtragem/segmentação adaptativas e morfologia. Uma nova rodada reproduziu o
mesmo hash SHA-256 do modelo ativo (`7ff8f83c00a7fbae729bcadd9cbffcd827c08356a60b5d9f0df898d26e6bc500`)
e as mesmas métricas; não houve ganho de reconhecimento nem troca de artefato.

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
