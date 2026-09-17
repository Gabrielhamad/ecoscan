# Fases 2 e 3: processamento, filtros e segmentação

## Objetivo

Implementar um pipeline demonstrável para uma imagem contendo um resíduo principal, cobrindo:

- carregamento;
- validação;
- correção/conversão para RGB;
- redimensionamento;
- normalização;
- filtragem;
- segmentação;
- preparação da entrada do modelo;
- geração de evidências visuais.

## Decisão técnica

O projeto foi estruturado para usar OpenCV quando disponível. Como o runtime atual ainda não possui `opencv-python`, alguns filtros têm fallback em Pillow/NumPy:

- Gaussiano: OpenCV ou Pillow;
- Mediana: OpenCV ou Pillow;
- CLAHE: OpenCV; fallback atual faz equalização global de histograma;
- Sobel: NumPy;
- Canny: OpenCV; fallback atual aplica limiar sobre magnitude Sobel;
- Bilateral: exige OpenCV.

Essa decisão preserva execução local imediata e mantém compatibilidade com a stack esperada da APS.

## Pipeline implementado

Arquivo principal: `src/ecoscan/app/pipeline.py`.

Etapas:

1. carregar imagem validada;
2. corrigir orientação EXIF;
3. converter para RGB;
4. redimensionar para `224x224`;
5. aplicar filtragem configurável ou pipeline adaptativo;
6. medir qualidade antes e depois do filtro;
7. aplicar segmentação configurável;
8. identificar componentes/elementos visuais significativos na máscara;
9. preparar imagem normalizada em `[0, 1]`;
10. gerar preview da imagem entregue ao modelo.

## Filtros implementados

Arquivo: `src/ecoscan/image_processing/filters.py`.

### Automático adaptativo

Modo padrão profissional. Analisa brilho, contraste, saturação, nitidez e densidade de bordas, testa sequências curtas de filtros e escolhe a preparação com melhor equilíbrio entre melhoria visual e preservação do resíduo. As candidatas incluem controle sem filtro, Gaussiano, mediana, bilateral, CLAHE e combinações como `clahe -> median` ou `clahe -> gaussian`. A decisão é registrada no metadata com pontuação e motivo.

### Sem filtro

Controle experimental. Serve para comparar se filtros melhoram ou prejudicam a imagem.

### Gaussiano

Suaviza ruídos de alta frequência. Pode ajudar antes de segmentação por limiar, mas também pode borrar bordas finas.

### Mediana

Reduz ruído impulsivo preservando bordas melhor que média simples.

### Bilateral

Preserva bordas enquanto suaviza regiões semelhantes. Requer OpenCV.

### CLAHE

Melhora contraste local no canal de luminosidade quando OpenCV está disponível. Sem OpenCV, o fallback é apenas equalização global, documentada como aproximação.

### Sobel

Realça gradientes e bordas. Útil para análise técnica de contornos, mas normalmente não deve ser a entrada final de um classificador RGB sem teste comparativo.

### Canny

Com OpenCV, usa detecção de bordas com histerese. Sem OpenCV, o fallback aplica limiar sobre Sobel, útil apenas para comparação inicial.

Observação: Sobel e Canny são mantidos como filtros de análise de bordas. O modo automático não os usa como entrada principal do classificador, porque eles removem informação de cor e textura importante para reconhecer resíduos.

## Segmentação implementada

Arquivo: `src/ecoscan/segmentation/methods.py`.

### Sem segmentação

Controle experimental para medir se segmentar ajuda ou prejudica.

### Otsu

Calcula um limiar global automático em tons de cinza. Funciona melhor quando há contraste entre resíduo e fundo.

### HSV

Planejado para destacar objetos coloridos por saturação/brilho. Requer OpenCV.

### GrabCut

Segmentação por primeiro plano/fundo a partir de retângulo central. Requer OpenCV e funciona melhor com objeto dominante centralizado.

## Análise de elementos visuais

Arquivo: `src/ecoscan/segmentation/elements.py`.

Depois da segmentação, a máscara é analisada por componentes conectados. O sistema estima quantos elementos significativos existem, área relativa, centroide, caixa delimitadora e se o componente toca a borda. Isso ajuda a demonstrar tecnicamente quando a imagem parece ter um resíduo principal ou múltiplos elementos visuais.

## Scripts de demonstração

Rodar pipeline completo:

```powershell
python scripts\run_processing_demo.py --image data\raw\metal\metal_0001_12-ounce-aluminum-soda-can-32167233397.jpg --filter gaussian --segmentation otsu
```

Comparar filtros:

```powershell
python scripts\compare_filters.py --image data\raw\metal\metal_0001_12-ounce-aluminum-soda-can-32167233397.jpg
```

Comparar segmentações:

```powershell
python scripts\compare_segmentation.py --image data\raw\metal\metal_0001_12-ounce-aluminum-soda-can-32167233397.jpg
```

## Evidências geradas

Os scripts salvam imagens e JSONs em:

- `reports/processing_demo`;
- `reports/filter_experiments`;
- `reports/segmentation_experiments`.
- exportações individuais também incluem `07_elements_overlay.jpg` e `08_detection_heatmap.jpg`.

O overlay mostra os componentes segmentados e o mapa de detecção evidencia, em cores quentes, a região considerada como resíduo na imagem. Esses arquivos são úteis para a tela "Ver Processamento" e para o relatório acadêmico.
