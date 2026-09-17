# EcoScan: base para relatório acadêmico

## Problema

Pessoas comuns frequentemente têm dúvidas sobre como descartar resíduos. Isso pode levar ao envio de recicláveis para lixo comum, descarte incorreto de resíduos orgânicos e tratamento inadequado de pilhas, baterias e eletrônicos.

## Objetivo

Desenvolver uma aplicação local que utilize processamento digital de imagens e visão computacional para classificar uma imagem contendo um resíduo principal e apresentar uma orientação de descarte configurável.

## Dataset

O dataset deve ser organizado por classe em `data/raw`. Antes do treinamento, o projeto executa análise exploratória para levantar quantidade de imagens por classe, resoluções, arquivos inválidos, exemplos aleatórios e problemas potenciais.

## Aquisição

A aquisição já contempla upload, captura estática por câmera no navegador e modo ao vivo mobile com preferência por câmera traseira. Em todos os casos, a imagem ou frame passa pelo pipeline local antes do reconhecimento.

## Manipulação e pré-processamento

O pipeline será parametrizável, com redimensionamento, correção de orientação, normalização e conversões de espaço de cor quando tecnicamente justificadas.

## Filtros

Filtros como Gaussiano, mediana, bilateral, CLAHE, Sobel e Canny serão avaliados experimentalmente. Cada filtro deverá ter objetivo, parâmetros, efeito esperado, resultado observado, vantagens e limitações.

## Segmentação

Segmentação será tratada como experimento, não como obrigação artificial. Threshold, HSV, contornos, watershed e GrabCut serão avaliados conforme fundo, iluminação e contraste das imagens reais.

## Modelagem

O objetivo inicial é classificação de uma imagem com um resíduo principal. A arquitetura está preparada para baseline e transfer learning, mas a escolha final depende dos dados.

## Treinamento

O treinamento deverá registrar seed, parâmetros, histórico, melhor modelo, validação e gráficos de loss/accuracy.

## Testes

A base atual possui testes para configuração, orientações separadas do modelo, análise exploratória de dataset, processamento, segmentação, inferência, câmera, tracking visual e pacote de entrega.

## Tratamento de erros

O projeto usa um contrato centralizado para apresentar falhas com código, mensagem amigável e ação recomendada. Detalhes técnicos ficam disponíveis para log e diagnóstico, sem expor stack trace bruto ao usuário.

## Resultados

Resultados definitivos ainda dependem do dataset real do grupo. A versão atual apresenta baseline, métricas exportáveis e rejeição por baixa confiança, sem tratar a baseline como modelo final.

## Limitações

O sistema não reconhece qualquer objeto existente. O escopo é controlado pelas classes configuradas. Imagens fora do domínio deverão ser tratadas por limiar de baixa confiança.

## Conclusão

O EcoScan estabelece uma base técnica e acadêmica completa para a APS, preservando evidências do processo e preparando o projeto para experimentos reprodutíveis quando o dataset definitivo for adicionado.
