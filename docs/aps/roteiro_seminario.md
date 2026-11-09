# Seminário EcoScan — roteiro de 13 minutos

Base: `89622ec714b815c216a9215ab9ba69999b39c6b8`. Roteiro pronto para revisão;
ensaio, fotos reais autorizadas e computador da apresentação: `manual_pending`.
Cada bloco terá responsável designado pelo grupo; não se presume número de integrantes.

| Tempo | Bloco e fala/ação | Evidência que deve aparecer |
| --- | --- | --- |
| 00:00–01:30 | Problema e sustentabilidade: dúvidas na separação, apoio educativo, redução/reutilização antes da reciclagem. Explicar o limite da foto. | Introdução, PNRS e objetivos; nenhum número de impacto ambiental inventado |
| 01:30–04:00 | Pipeline PDI: abrir foto real autorizada A; original, RGB/cinza/histograma, controle, Gaussiano/mediana, Otsu/HSV, máscara, abertura/fechamento e componentes. Mostrar parâmetros e diferença medida. | Exportação da mesma execução, hash e limite de máscara; algoritmos próprios versus bibliotecas |
| 04:00–06:30 | Demo de reconhecimento: usar a próxima foto da lista congelada antes do ensaio. Mostrar hipótese original ou rejeição, qualidade e entrada RGB do encoder. Não tratar score como certeza. | SHA/configuração, saída antes da confirmação e indicação de confirmação obrigatória |
| 06:30–08:15 | Erro e correção: mostrar um erro real encontrado na coleta, sem descartá-lo. Registrar previsão e rótulo, corrigir manualmente e explicar hipóteses de causa apenas se a foto as sustentar. | Antes/depois da correção; manter o erro no relatório. Sem novo caso disponível, discutir o erro histórico documentado: 3/29 metais tiveram top-1 vidro; não encenar uma foto como esse erro |
| 08:15–09:15 | Descarte: confirmar a categoria e mostrar cor/ponto correspondente. Distinguir “modelo sugeriu”, “pessoa confirmou” e orientação ambiental. | Metal amarelo/plástico vermelho/vidro verde/papel azul; pilhas/eletrônicos em rota especial, aceitação a conferir |
| 09:15–11:30 | Testes e resultados: top-1, matriz, erros, rejeição e cobertura. Explicar 101/145 e 51 aceitos pelo artefato, 94 rejeitados; não chamar esse histórico de validação independente. Mostrar CI e um teste pixel a pixel. | Índice, JSON histórico e CI do SHA correto; dados de laboratório versus campo separados |
| 11:30–13:00 | Conclusão: o que o programa implementa, o que os dados sustentam e o que falta validar. Apresentar apêndice e pendência da ficha/manual oficial. | Limitações, confirmação humana, próximos experimentos e autoria real em material privado |

## Preparação da seleção e das figuras

1. Reunir fotos reais autorizadas sem rosto, endereço residencial ou outros dados
   pessoais. Registrar licença/consentimento, hash, rótulo conferido, objeto e sessão.
2. Congelar ordem antes de executar o modelo: por exemplo, ordem de coleta, sem
   excluir erros/rejeições. Identificar A/B e um caso difícil; fotos não precisam
   ter sido escolhidas por acerto. Não usar treino para alegar desempenho de campo.
3. Registrar todo o lote: sugestão original, rejeição, confirmação e destino.
   Se não existir erro no pequeno lote, manter esse resultado, mostrar o erro
   histórico da matriz e dizer que sua foto não acompanha o clone. Não fabricar erro.
4. Em outro ensaio, usar foto real B para comparar filtros e segmentação. Se houver
   sombra/reflexo/transparência, diagnosticar o que de fato se vê. Guardar também
   um caso em que o método falhe. Sem máscara humana, dizer “IoU/Dice não medidos”.

Na main congelada, filtros comuns ainda podem alterar a entrada do encoder.
Executar a demo oficial com os defaults registrados; a exploração didática não
deve ser apresentada como evidência de invariância já implementada. A máscara é
diagnóstica. Não atribuir os recursos dos PRs ainda abertos ao site publicado.

## Contingências e ensaios

Preparar instalação, modelo/shards, foto autorizada offline e navegador no PC real
antes do seminário. Se câmera/rede falhar, usar upload local **previamente testado**.
Se o modelo falhar, mostrar a falha e a alternativa humana disponível no SHA
testado; não prometer o fluxo resiliente do PR #26 na main antiga. Não entrar em
contas reais ou abrir Secrets durante a apresentação.

| Ensaio | Data/SHA/dispositivo/navegador | Duração medida | Erros/rejeições/ocorrências | Status |
| --- | --- | --- | --- | --- |
| 1 | A preencher | Não medida | A preencher | `manual_pending` |
| 2 | A preencher | Não medida | A preencher | `manual_pending` |
| 3 | A preencher | Não medida | A preencher | `manual_pending` |

A faixa de 10–15 minutos é meta do roteiro; não é um resultado de ensaio. Se o
programa mudar, congelar novo SHA e repetir os cenários afetados. As fotos e os
resultados reais entram somente depois de disponíveis e revisados.
