# Pipeline profissional de filtragem e reconhecimento

Este documento descreve a versão atual do pipeline usado pelo EcoScan para atender à etapa da APS de filtrar/processar a imagem e depois realizar reconhecimento.

## Fluxo técnico

```text
imagem original
-> validação
-> correção de orientação e RGB
-> redimensionamento
-> análise de qualidade
-> filtro automático ou manual
-> nova análise de qualidade
-> segmentação adaptativa ou manual
-> análise de elementos visuais segmentados
-> diagnóstico de qualidade da captura
-> preparação para o modelo
-> reconhecimento/classificação
-> orientação de descarte
```

## Câmera

O EcoScan possui dois caminhos de câmera:

- interface Streamlit: usa a câmera do navegador com `st.camera_input`, sem exigir OpenCV;
- script local: `scripts/capture_webcam.py`, que usa OpenCV para capturar um frame, rodar inferência e exportar evidências.
- modo ao vivo mobile: `scripts/run_live_camera_app.py`, que abre uma página web própria, prioriza a câmera traseira do celular e envia frames ao backend local.

Exemplo:

```powershell
python scripts\capture_webcam.py --camera-index 0 --filter auto --segmentation auto
```

As evidências do script são salvas em `reports/camera_detection`.

No modo ao vivo, a página desenha caixas com IDs de tracking sobre os componentes segmentados. A classificação ainda é feita sobre o frame/resíduo principal; as caixas são uma camada geométrica de rastreamento, não um detector treinado de múltiplas classes por objeto.

## Filtragem adaptativa

O modo `auto` avalia:

- brilho médio;
- contraste;
- nitidez;
- saturação;
- densidade de bordas.

Com base nisso, o pipeline monta e compara sequências curtas de preparação da imagem. As sequências candidatas incluem:

- `none`, para controle experimental;
- `gaussian`, para suavização leve;
- `median`, para ruído impulsivo e excesso de bordas;
- `bilateral`, para suavizar preservando bordas quando OpenCV está disponível;
- `clahe`, para baixo contraste ou exposição irregular;
- combinações como `clahe -> median`, `clahe -> gaussian` e `clahe -> bilateral`.

O EcoScan pontua cada candidata por contraste, exposição, densidade de bordas, nitidez, preservação de cor e complexidade da sequência. A decisão fica registrada em `metadata["filter"]["decision"]`, incluindo sequência escolhida, motivo, métricas das candidatas e sequências ignoradas por dependência indisponível.

Sobel e Canny continuam disponíveis para estudo de bordas e comparação visual, mas não entram no modo automático como preparação principal do classificador. Eles transformam a foto em mapa de bordas e, por isso, são mais adequados como evidência técnica do que como substitutos diretos da imagem RGB.

## Segmentação adaptativa e elementos visuais

O modo padrão da segmentação agora é `auto`. Nesse modo, o EcoScan avalia métodos candidatos e escolhe a melhor máscara para cada imagem. A decisão considera proporção de primeiro plano, contato com bordas, componentes relevantes, saturação, contraste e densidade de bordas.

Métodos candidatos:

- `otsu`: bom para objeto e fundo com contraste global claro;
- `hsv_color`: útil quando o resíduo se destaca por cor, com fallback em NumPy;
- `grabcut`: útil para objeto centralizado em fundo mais complexo, quando OpenCV está disponível.

A decisão fica registrada em `metadata["segmentation"]["decision"]`, incluindo método solicitado, método escolhido, motivo, candidatos avaliados e métodos ignorados por dependência indisponível.

Após a segmentação, o sistema analisa a máscara e identifica componentes conectados significativos. Para cada elemento visual, ele calcula:

- caixa delimitadora;
- centroide;
- área em pixels;
- área relativa;
- se toca a borda da imagem.

Essa etapa ajuda a explicar se a segmentação isolou um resíduo principal ou se a imagem possui múltiplos componentes relevantes.

Importante: isso ainda não é detecção treinada de múltiplos objetos. É uma análise geométrica da máscara segmentada, adequada para o MVP de uma imagem com um resíduo principal.

## Diagnóstico de captura

Depois de filtrar e segmentar, o EcoScan avalia se a imagem realmente ficou adequada para leitura. O sistema pode retornar:

- `good`: captura adequada;
- `attention`: captura utilizável com ajustes;
- `retake`: nova captura recomendada.

Essa decisão usa exposição, contraste, foco, densidade de bordas, quantidade de elementos segmentados e tamanho do resíduo no enquadramento. O objetivo é orientar o usuário quando o melhor tratamento não é outro filtro, mas uma nova foto com melhor luz, fundo simples, foco correto ou apenas um resíduo por vez.

## Processamento por foto

Cada foto analisada recebe um resumo técnico próprio. A interface mostra:

- filtragem ou sequência de filtros usada na foto;
- segmentação escolhida para aquela imagem;
- motivo da escolha automática;
- quantidade de elementos visuais relevantes encontrados;
- qualidade da captura e ação recomendada.

Quando o histórico local é ativado, esses dados também são salvos junto com a classe, confiança e modelo usado. Assim, duas fotos diferentes podem ter decisões diferentes, por exemplo uma usando `clahe -> median` por baixo contraste e fundo complexo, e outra usando `bilateral` por já estar bem iluminada, mas com textura de fundo.

## Reconhecimento

O reconhecimento atual usa a baseline acadêmica disponível em `models/baseline_classifier.json`. Ela permite demonstrar o fluxo completo, mas o modelo final deve ser treinado depois do dataset real e curado.

## Evidências exportadas

Ao exportar evidência técnica, o sistema salva:

- `01_original.jpg`;
- `02_resized.jpg`;
- `03_filtered.jpg`;
- `04_segmentation_mask.jpg`;
- `05_segmented.jpg`;
- `06_model_input_preview.jpg`;
- `07_elements_overlay.jpg`;
- `08_detection_heatmap.jpg`;
- `pipeline_overview.jpg`;
- `pipeline_report.json`.

O `08_detection_heatmap.jpg` sobrepõe a máscara em cores quentes sobre a imagem, destacando visualmente a região usada na análise. Esses arquivos servem diretamente para a apresentação e para o relatório da APS.

## Limite honesto do MVP

O EcoScan já filtra, segmenta, analisa componentes e reconhece uma classe. A versão final com detecção de todos os resíduos em uma cena exigirá dataset anotado por caixas ou máscaras e um detector como YOLO, Faster R-CNN ou equivalente.
