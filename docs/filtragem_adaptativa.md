# Filtragem adaptativa do EcoScan

## Objetivo

A filtragem adaptativa foi adicionada para que o EcoScan não aplique sempre o mesmo tratamento em todas as imagens. Cada foto de resíduo pode vir com iluminação, ruído, contraste, fundo e foco diferentes. Por isso, o modo `auto` avalia a imagem e escolhe uma sequência curta de filtros antes da segmentação e do reconhecimento.

## Métricas analisadas

O sistema mede:

- brilho médio, para identificar subexposição ou superexposição;
- contraste, para saber se objeto e fundo estão pouco separados;
- nitidez, por variância do Laplaciano;
- saturação média, para preservar informação de cor;
- densidade de bordas, para estimar ruído visual ou fundo complexo.

## Sequências avaliadas

As candidatas principais são:

- `none`: controle experimental;
- `gaussian`: suavização leve;
- `median`: redução de ruído impulsivo;
- `bilateral`: suavização com preservação de bordas, quando OpenCV está disponível;
- `clahe`: melhoria de contraste local;
- `clahe -> gaussian`;
- `clahe -> median`;
- `clahe -> bilateral`.

O limite padrão é de duas etapas para evitar excesso de processamento e perda de informação útil ao classificador.

## Como a decisão é tomada

Cada candidata recebe uma pontuação considerando:

- exposição em faixa adequada;
- contraste suficiente;
- densidade de bordas equilibrada;
- preservação de nitidez;
- preservação de cor;
- penalização leve para sequências mais longas.

Se a imagem tem baixo contraste ou exposição ruim, sequências com CLAHE são priorizadas. Se a imagem tem excesso de bordas, sequências com mediana, Gaussiano ou bilateral ganham prioridade. Se a imagem está adequada, o sistema prefere uma preparação leve.

## Uso no pipeline

O resultado é salvo em `metadata["filter"]["decision"]`, com:

- sequência escolhida;
- motivo da escolha;
- problemas de qualidade detectados;
- tabela de candidatas avaliadas;
- sequências ignoradas por dependência indisponível.

Sobel e Canny permanecem disponíveis para análise de bordas e comparação técnica, mas não são usados no modo automático como entrada principal do reconhecimento porque descartam informação de cor e textura.

## Relação com a segmentação

A filtragem adaptativa acontece antes da segmentação adaptativa. Assim, a máscara recebe uma imagem já preparada de acordo com a condição real da foto. Depois disso, o EcoScan escolhe entre Otsu, HSV e GrabCut conforme a máscara gerada e as características da imagem.

## Qualidade da captura

Depois da filtragem e da segmentação, o EcoScan também emite um diagnóstico de captura:

- `good`: a imagem está adequada;
- `attention`: a imagem pode ser usada, mas há ajustes recomendados;
- `retake`: é melhor capturar novamente.

Esse diagnóstico considera a qualidade antes e depois do filtro, além da máscara segmentada. Se o resíduo estiver pequeno demais, sem foco, muito escuro, muito claro, com fundo complexo ou com vários objetos na cena, o sistema orienta a ação prática: melhorar iluminação, trocar fundo, aproximar a câmera, estabilizar o foco ou analisar um resíduo por vez.
