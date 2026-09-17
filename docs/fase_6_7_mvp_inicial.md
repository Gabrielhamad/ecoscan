# Fases 6 e 7: pipeline integrado e interface inicial

## Objetivo

Integrar processamento, baseline de classificação e orientação de descarte em um fluxo de aplicação.

## Serviço de análise

Arquivo: `src/ecoscan/services/analysis_service.py`.

Responsabilidades:

- executar o pipeline de processamento;
- carregar o modelo baseline;
- calcular a classe mais provável;
- aplicar limiar de rejeição;
- buscar orientação em `config/disposal_guidance.json`;
- devolver uma resposta única para UI ou CLI.

## Inferência por linha de comando

```powershell
python scripts\run_inference.py --image data\raw\metal\metal_0001_12-ounce-aluminum-soda-can-32167233397.jpg
```

O script exibe:

- tipo do modelo;
- classe mais próxima;
- classe aceita ou `__uncertain__`;
- probabilidade/score;
- orientação, quando houver confiança suficiente.

## Interface Streamlit

Arquivo: `src/ecoscan/ui/streamlit_app.py`.

Execução:

```powershell
python scripts\run_streamlit_app.py
```

A interface possui:

- upload de imagem;
- captura por câmera via navegador;
- seleção de filtro;
- seleção de segmentação;
- resultado da classificação;
- orientação de descarte;
- área "Ver processamento";
- scores por classe.

## Estado do MVP

O fluxo já está integrado com baseline, mas o modelo final ainda precisa ser treinado com transfer learning. Por isso, os resultados atuais devem ser apresentados como baseline acadêmica e não como classificador definitivo.

Exemplo observado em imagem de teste da classe `metal`: a baseline KNN apontou `organic` como classe mais próxima, mas com score 0.444, abaixo do limiar 0.45. O sistema respondeu como incerto, o que demonstra o mecanismo de rejeição solicitado no manual da APS.
