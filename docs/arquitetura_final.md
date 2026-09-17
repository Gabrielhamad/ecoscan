# Arquitetura final preparada

## Camadas

### Interface

`src/ecoscan/ui/streamlit_app.py`

- upload;
- câmera via navegador;
- resultado;
- orientação;
- seleção de perfil local;
- campanha, conta do usuário e denúncia;
- painel administrativo de gestão;
- visão geral executiva do projeto;
- barras de confiança por classe;
- detalhes do processamento;
- scores por classe;
- histórico local;
- mensagens de erro padronizadas.

`src/ecoscan/live_camera`

- servidor web local para reconhecimento ao vivo;
- página mobile com preferência por câmera traseira;
- envio periódico de frames ao backend;
- painel inferior responsivo para leitura em celular;
- barras de confiança no modo ao vivo;
- overlay com caixas e IDs de tracking;
- rastreamento geométrico dos componentes segmentados.

### Processamento de imagem

`src/ecoscan/image_processing`

- validação;
- leitura RGB;
- redimensionamento;
- normalização;
- filtros.

### Segmentação

`src/ecoscan/segmentation`

- sem segmentação;
- Otsu;
- HSV com OpenCV;
- GrabCut com OpenCV.

### Classificação

`src/ecoscan/classification`

- baseline KNN;
- baseline por centróide;
- inferência;
- carregamento de modelo final `.keras`.

### Treinamento

`src/ecoscan/training`

- plano de transfer learning;
- treinamento TensorFlow preparado;
- MobileNetV2, EfficientNetB0 e ResNet50 como arquiteturas suportadas.

### Regras de descarte

`src/ecoscan/disposal`

O modelo só classifica. As orientações ficam em `config/disposal_guidance.json`.

### Serviços

`src/ecoscan/services`

- análise de imagem;
- análise exploratória;
- divisão de dataset;
- revisão/curadoria;
- histórico;
- perfis locais, pontuação e ranking;
- campanha e missões;
- operação de campanhas da secretaria;
- denúncias e revisão administrativa;
- relatórios visuais;
- status do projeto;
- prontidão final e trilhas de evolução;
- validação executável de aceite;
- pacote de entrega APS.

### Logs

`src/ecoscan/utils/logging_config.py`

- arquivo local `logs/ecoscan.log`;
- registro de inferência, modelo, classe, score, filtro, segmentação e tempo;
- registro técnico de falhas para diagnóstico sem expor stack trace bruto na interface.

### Tratamento de erros

`src/ecoscan/errors.py`

- código de erro;
- título e mensagem para usuário;
- ação recomendada;
- detalhe técnico controlado para log e diagnóstico;
- payload público reutilizado pela interface e pelo EcoScan Live.

### Métricas

`src/ecoscan/metrics`

- accuracy;
- precision;
- recall;
- F1;
- matriz de confusão;
- exportação CSV/PNG.

### Detecção futura

`src/ecoscan/detection`

Existe contrato reservado para detecção treinada de múltiplos resíduos por classe, mas a feature está explicitamente desativada no MVP. O modo ao vivo atual rastreia componentes segmentados e classifica o frame/resíduo principal.

## Decisão de modelo

O app está preparado para dois cenários:

1. `models/ecoscan_transfer.keras` existe: usa modelo final TensorFlow.
2. Modelo final não existe: usa `models/baseline_classifier.json`.

Essa escolha permite apresentar a aplicação agora e trocar o motor quando houver dataset suficiente.
