# Diagnóstico da Fase 1

## Estado do repositório

O workspace já continha um projeto Java/Web relacionado ao Rio Tietê, com diretórios como `src/br/edu/redestiete`, `config`, `data`, `scripts` e `barbearia-caixa`.

Também havia alterações pendentes no Git antes do início desta fase. Por isso, o EcoScan foi criado em uma pasta isolada:

```text
ecoscan/
```

Essa separação evita colisão com o projeto existente, principalmente porque a raiz já possui diretórios `data` e `config` usados por outro sistema.

## Arquitetura proposta

O EcoScan seguirá uma arquitetura modular:

- `app`: coordenação dos fluxos da aplicação;
- `image_processing`: aquisição, validação, manipulação, filtros e pré-processamento;
- `segmentation`: experimentos e pipeline de segmentação;
- `classification`: baseline, transfer learning, treinamento e inferência;
- `disposal`: regras e orientações de descarte;
- `services`: casos de uso reutilizáveis, como análise de dataset;
- `ui`: interface Streamlit ou alternativa futura;
- `metrics`: métricas de treinamento e avaliação;
- `utils`: logging, caminhos e utilidades.

A decisão inicial para interface é Streamlit, por menor complexidade de instalação e boa experiência em apresentação acadêmica. PySide6/PyQt fica como alternativa caso a APS exija desktop.

## Decisões que dependem do dataset

- Classes finais: as sete classes iniciais são configuráveis, mas podem mudar se houver poucas imagens ou muita confusão visual.
- Modelo final: MobileNetV2, MobileNetV3, EfficientNetB0 e ResNet50 ainda precisam ser comparados em tempo, tamanho e métricas.
- Segmentação final: não será forçada; será escolhida após experimentos com imagens reais.
- Filtros finais: Gaussian, mediana, bilateral, CLAHE, Sobel e Canny serão avaliados conforme ruído, iluminação e fundo do dataset.
- Data augmentation: depende da variação real dos objetos e não deve alterar semanticamente as classes.
- Limiar de confiança: começou em `0.65`, mas deve ser calibrado com validação.
- Separação treino/validação/teste: deve evitar vazamento, especialmente imagens quase idênticas do mesmo objeto.

## Plano da Fase 1

1. Criar pasta isolada do EcoScan.
2. Criar estrutura de módulos e diretórios acadêmicos.
3. Centralizar configurações em `config/settings.json`.
4. Criar base de orientações em `config/disposal_guidance.json`.
5. Implementar validação de imagem.
6. Implementar análise exploratória de dataset.
7. Gerar relatórios em `reports`.
8. Criar testes automatizados para configuração, orientação e análise do dataset.
9. Documentar execução e decisões pendentes.

## Resultado da Fase 1

A Fase 1 entrega um projeto executável e preparado para receber dataset real, sem inventar métricas ou modelo antes dos dados.
