# Prática de processamento digital de imagens

O EcoScan permite demonstrar o tratamento da imagem antes do reconhecimento.
Este roteiro conecta conceitos usuais da disciplina à implementação e às
evidências. Conferir com o professor a lista e o formato específicos da avaliação;
a ementa oficial não foi fornecida.

## Como acessar

- Visitante/participante: expandir **Laboratório de processamento de imagens** na
  página principal. Selecionar os parâmetros e tirar/enviar a foto em Escanear.
  O resultado exibe **Processamento aplicado: antes e depois**, sem exigir abrir a área técnica.
  As abas apresentam o antes/depois e a diferença de cada operação.
  **Baixar evidências do processamento (ZIP)** salva PNGs, cinza/histogramas, parâmetros CSV, hashes, tempos e relatório Markdown. O pacote contém a foto e não atesta sua origem.
- Analista: usar os **Parâmetros técnicos** na barra lateral e a aba **Processamento**.
- Mudar uma operação ou parâmetro reprocessa a foto carregada; não é necessário
  reenviar uma contribuição à secretaria.
- Para demonstrar sem login, modelo treinado ou banco: executar o experimento
  sintético descrito abaixo.

## Sequência real do pipeline

    Arquivo validado e orientação EXIF corrigida
      → conversão RGB e transparência sobre branco
      → redução proporcional por área (lado maior até 640 px)
      → diagnóstico e filtragem
      → segmentação (máscara binária)
      → abertura + fechamento da máscara (padrão ativo)
      → máscara aplicada somente à prévia diagnóstica
      → componentes, área e caixas
      → RGB completo com margens para o classificador (224×224)
      → reconhecimento e orientação

A imagem original é preservada em memória. A máscara bruta e a máscara tratada
são mantidas separadamente. O padrão seleciona **filtragem e segmentação
adaptativas → abertura + fechamento**, com elemento quadrado 3×3, uma iteração
por primitiva e borda zero. Para demonstrar especificamente mediana 3×3 e Otsu,
selecione esses métodos no laboratório.
A máscara tratada não apaga pixels da entrada de reconhecimento. A versão
[RGB preservado v2](processamento_preservado_v2.md) mantém cor e proporções.
Os parâmetros são configurados em config/settings.json; o avaliador também lê esses padrões.
Os controles sem operação e os métodos manuais continuam disponíveis no laboratório.

## Conteúdo da disciplina e onde demonstrar

| Conceito | Aplicação no EcoScan | Evidência |
| --- | --- | --- |
| Aquisição e validação | Upload/câmera; formato, arquivo vazio, dimensão, orientação e RGB | Original, dimensões e testes de imagem |
| Amostragem e interpolação | Redução por área preservando proporções; margens para tamanho fixo | Escala, dimensões, caixa de conteúdo e imagem preparada |
| Intensidade e cor | RGB preservado; luminância aproximada para tons de cinza; HSV na segmentação por cor | RGB, cinza e histograma |
| Normalização | Conversão de uint8 para float32 em [0,1] como preparação de referência | Tipo, intervalo e forma do tensor |
| Filtragem | Gaussiano, mediana, bilateral e CLAHE; opção sem filtro e seleção adaptativa | Antes/depois e parâmetros |
| Bordas | Sobel e Canny disponíveis para experimento | Resposta visual de bordas |
| Segmentação | Otsu, seleção por saturação/brilho em HSV e GrabCut | Máscara e imagem segmentada |
| Morfologia | Erosão, dilatação, abertura, fechamento e abertura seguida de fechamento | Máscara antes/depois, kernel e estágios |
| Contorno morfológico | Gradiente da máscara final | Diferença entre dilatação e erosão, somente para inspeção |
| Regiões | Componentes conectados, área, caixas e diagnósticos | Overlay e metadados de elementos |
| Avaliação | Diferenças medidas; IoU/Dice somente contra referência fornecida | Relatório por execução e comparação com controle |

Os tons de cinza usam 0,299R + 0,587G + 0,114B, com saída uint8.
O histograma conta pixels por intensidade de 0 a 255. Não é um gráfico de
confiança do modelo. HSV e GrabCut preservam o uso de cor; não se converte todo
o fluxo para cinza indiscriminadamente.

O redimensionamento preserva a proporção e adiciona margens; não recorta nem
estica o objeto. A release ativa `semantic_onnx_assisted` utiliza um encoder
CLIP exportado para ONNX e uma cabeça supervisionada. A entrada efetiva é o RGB
preparado em 224×224, normalizado no classificador; a sugestão de classe sempre
exige confirmação humana. A máscara de segmentação não modifica essa entrada.

## Escolha das técnicas

| Situação observada | Experimento indicado | O que conferir |
| --- | --- | --- |
| Ruído pontual claro/escuro no RGB | Mediana versus sem filtro | Redução do ruído e preservação das bordas |
| Ruído estimado | Gaussiano/bilateral versus controle | Redução do ruído sem apagar textura e detalhes relevantes |
| Contraste local baixo | CLAHE versus controle | Contraste, artefatos e ruído amplificado |
| Objeto com fundo contrastante | Otsu e polaridade clara/escura | Se branco corresponde realmente ao objeto |
| Objeto colorido | HSV com limites de saturação e brilho | Fundo colorido e objetos transparentes podem falhar |
| Objeto centralizado | GrabCut | Margem, fundo e exclusão de partes do objeto |
| Pontos brancos isolados na máscara | Abertura | Remoção de ruído sem apagar peças pequenas |
| Pequenas lacunas pretas dentro do objeto | Fechamento | Preenchimento sem unir objetos diferentes |
| Fragmentos separados por distância pequena | Dilatação controlada | Conexão desejada versus fusão indevida |
| Regiões unidas por ponte fina | Erosão controlada | Separação versus desaparecimento do objeto |

Sobel/Canny descrevem bordas; não são equivalentes à máscara preenchida do
primeiro plano. No laboratório, eles não substituem o RGB entregue ao modelo.
A seleção adaptativa existente é heurística,
não uma garantia de melhor técnica.

## Contrato das operações morfológicas

Trabalham na máscara binária: fundo 0 e primeiro plano 255. Não são aplicadas
diretamente às três bandas de cor. O padrão **abertura + fechamento** executa
as quatro primitivas. Para comparar com o controle, selecionar explicitamente
**Sem morfologia**. O gradiente continua apenas diagnóstico.

- Erosão mantém um pixel quando toda a vizinhança ativa do kernel é primeiro plano.
- Dilatação mantém um pixel quando pelo menos uma posição ativa é primeiro plano.
- Abertura executa erosão seguida de dilatação.
- Fechamento executa dilatação seguida de erosão.
- Abertura + fechamento executa erosão, dilatação, dilatação e erosão.
- Gradiente exibe o contorno pela diferença dilatação menos erosão; não substitui
  a imagem RGB usada pelo classificador.

Parâmetros disponíveis:

| Parâmetro | Valores | Significado |
| --- | --- | --- |
| Formato | Quadrado, cruz ou disco | Define a vizinhança; disco usa distância euclidiana no grid |
| Tamanho | Ímpar, de 1 a 15 pixels | Dimensões do elemento; 1 é controle de identidade |
| Iterações | De 1 a 5 | Repetições de cada primitiva |
| Âncora | Centro do elemento | Posição alinhada ao pixel tratado |
| Borda | Fundo constante zero | Hipótese explícita sobre pixels fora da imagem |

Com duas iterações, abertura significa **duas erosões e depois duas dilatações**,
não duas aberturas completas. O kernel efetivo e a ordem estão no JSON.
O disco discretizado não deve ser confundido com qualquer convenção de elipse
de biblioteca.

Como a borda externa é zero, a erosão pode retirar partes de objetos que tocam
o limite da foto. Elementos grandes podem eliminar completamente objetos finos;
a interface avisa quando a máscara tratada fica vazia ou totalmente preenchida.
Nenhuma máscara degenerada é silenciosamente substituída pela anterior.

## Evidência do antes e depois

A interface usa os arrays produzidos pela análise. Não repete as transformações
para produzir uma imagem ilustrativa. Cada primitiva morfológica recebe a máscara
de saída da anterior; a última máscara serve à prévia segmentada, aos contornos
e às medições. O classificador recebe o RGB filtrado e redimensionado, **sem
aplicação da máscara**. Os testes verificam a preservação dos pixels do objeto
e a correspondência das evidências exportadas com as operações executadas.

- Antes/depois de redimensionamento, filtro, segmentação, cada primitiva e aplicação da máscara.
- Diferença absoluta por pixel (máximo entre canais RGB), sem amplificação artificial.
- Pixels alterados, kernel, ordem, iterações e parâmetros efetivamente usados.
- Operação executada sem mudança é identificada como tal; controle desativado tem estado distinto.
- Em dimensões/representações distintas não se calcula diferença pixel a pixel.
- ZIP em memória por análise: PNGs sem perdas, prancha e manifesto com hashes de conteúdo.
  O manifesto do ZIP não inclui caminhos do servidor nem identidade da conta.

A prancha de antes/depois demonstra operações, não acurácia do classificador.
Os relatórios em `reports/` são ignorados pelo Git. Os exemplos de caminhos abaixo
são **placeholders locais**, não fotos existentes no repositório.

### Exportação acadêmica de fotos autorizadas

Na raiz do projeto, com Python 3.12 e as dependências declaradas:

```bash
python scripts/export_processing_evidence.py \
  --image /dados/aps/foto_autorizada.png --output reports/aps/foto_01 \
  --source-kind field_photo --consent --compare-filters \
  --segmentation otsu --morphology open_close
```

`--compare-filters` executa **controle, gaussiano, mediana e Sobel**, uma vez cada,
a partir do mesmo arquivo. Mantém os mesmos parâmetros solicitados de segmentação
e morfologia. Cada variante tem relatório e manifesto próprios. Para outra técnica:

```bash
python scripts/export_processing_evidence.py \
  --image /dados/aps/foto_autorizada.png --output reports/aps/foto_01_hsv \
  --source-kind field_photo --consent --filter median --segmentation hsv_color
```

`--filter`, `--segmentation` e `--morphology` substituem os padrões. `--options`
recebe um arquivo JSON com campos de `ProcessingPipelineOptions`, por exemplo:

```json
{
  "filter_parameters": {"kernel_size": 3},
  "segmentation_parameters": {"invert": true},
  "morphology_parameters": {"kernel_size": 3, "kernel_shape": "cross", "iterations": 1}
}
```

Parâmetros efetivos, inclusive limiar escolhido por Otsu e sequência adaptativa,
estão em `parameters.csv` e `manifest.json`. O manifesto inclui SHA do arquivo de
entrada, arrays, arquivos exportados, código, configuração, script e checkout,
versões das dependências, opções e contrato efetivo da prévia de reconhecimento.
O SHA do checkout sozinho não atesta árvore limpa: os hashes do código registram
as fontes efetivamente utilizadas. Arquivar também o diff se executar com alterações.

A origem e `--consent` são **declarações do operador**, não auditoria externa.
`--source-kind synthetic_fixture` identifica testes técnicos e não converte uma
fixture em evidência de campo. A UI exporta `source_kind=not_attested`, sem
alegar consentimento, e não tem hash do arquivo codificado já descartado; mantém
o hash do RGB original orientado. Nenhum nome de arquivo/caminho de upload ou
identidade de conta é incluído no pacote. O PNG original contém o RGB decodificado,
orientado e sem os metadados EXIF; não é cópia byte a byte do arquivo de entrada.

O diretório deve ser novo. `evidence.zip` e as figuras extraídas contêm os mesmos
bytes, sem segunda execução das operações. Para comparação, o ZIP contém as
subpastas das quatro variantes, `comparison.csv` e o relatório que referencia
cada execução. Para filtro único, os arquivos ficam diretamente na raiz:

- `00_original_rgb.png`, cinza e histogramas antes/depois; `histogram.csv` contém as 256 contagens exatas.
- `*_before.png`, `*_after.png`, `*_difference.png`: arrays de cada etapa, sem perdas.
- `components.png`, `contours.png`: caixas dos componentes e gradiente morfológico real.
- `parameters.csv`, `manifest.json`, `report.md`, `antes_depois.png`.
- `06_classifier_input_after.png`: RGB efetivamente preparado, sem máscara; não é previsão.

**Reprodutibilidade:** exportar duas vezes a mesma execução capturada produz ZIP
idêntico (ordem e timestamps fixos). Reprocessar a foto mede novos tempos; portanto
não promete ZIP byte idêntico entre execuções. Compare hashes dos arrays, opções,
contrato, código e versões. Pillow/OpenCV/fonte disponível ou versões diferentes
podem alterar PNGs e pranchas; a equivalência pixel a pixel deve usar o mesmo ambiente.
Os tempos são os realmente medidos no pipeline: decodificação, preparação,
filtro, segmentação e etapa conjunta de evidências/morfologia/entrada. Não se
inventa tempo por primitiva nem latência de inferência; a CLI não carrega o encoder.
A diferença média/máxima usa o mapa da maior diferença absoluta entre canais RGB
(ou diferença binária), em 0–255, sem amplificação e sem interpretação de qualidade.

**Limite da baseline `89622ec`:** a máscara é independente da entrada RGB, mas
filtros de cor podem alterar essa entrada. Este trabalho não muda a preparação do
classificador. A separação completa dos filtros didáticos é escopo do
[PR #21](https://github.com/Gabrielhamad/ecoscan/pull/21), pendente no `main`
consultado; não alegar compatibilidade homologada de todas as variantes.

### Referência humana opcional

1. Anotar manualmente o objeto no sistema de coordenadas de `01_resize_after.png`
   (ou `none/01_resize_after.png` na comparação), já orientado e reduzido.
2. Salvar PNG binário L/1 com exatamente a mesma largura/altura, fundo 0 e objeto
   255. Não usar RGB/paleta/cinza intermediário nem EXIF de rotação. Registrar
   autor/revisor, critério de contorno e limitações **fora do Git público**.
3. Em novo diretório, repetir a mesma execução adicionando
   `--reference-mask /dados/aps/mascara_revisada.png --reference-reviewed`.

A CLI rejeita referência sem revisão declarada, dimensões diferentes ou
conversão silenciosa. Calcula IoU/Dice contra máscaras bruta e final. Duas máscaras
vazias recebem 1 por convenção matemática, explicitamente registrada; isso não
valida a anotação de um objeto ausente. Sem referência, `reference_quality=null`
e células de métricas ficam vazias. Pixels alterados, área ou redução de
componentes não substituem IoU/Dice e não medem reconhecimento.

### Autoria das operações

| Operação | Implementação do projeto | Biblioteca utilizada |
| --- | --- | --- |
| Aquisição/RGB/EXIF/PNG | Validação, contratos e orquestração | Pillow para decodificar, orientar, compor alpha e exportar |
| Redução/margens | Geometria, opções e metadados | OpenCV por área/linear; Pillow bicúbico apenas no helper legado |
| Cinza/histograma | Fórmula RGB e contagens/bins | NumPy; Pillow desenha o gráfico exportado |
| Gaussiano/mediana/bilateral/CLAHE | Seleção, parâmetros e explicações | OpenCV; gaussiano/mediana têm fallback Pillow, sem promessa de igualdade numérica |
| Sobel | Vizinhanças, kernels, magnitude e normalização | NumPy; a função local aplica os kernels como correlação |
| Canny | Parâmetros e despacho | OpenCV; fallback NumPy é limiar Sobel, não Canny completo |
| Otsu | Histograma, variância entre classes, limiar e polaridade | NumPy; não chama `cv2.threshold` |
| HSV | Regras sobre saturação/brilho | OpenCV para RGB→HSV; cálculo NumPy no fallback |
| GrabCut | Retângulo, seed e conversão de rótulos em máscara | OpenCV para estimar primeiro plano/fundo |
| Morfologia/gradiente | Erosão/dilatação, sequência, kernel e borda zero | NumPy; não chama `cv2.morphologyEx` |
| Componentes/caixas | Busca em largura, 4 vizinhos, área e centroide | `deque`/NumPy; Pillow para desenhar caixas |

Não atribuir ao grupo a implementação interna dos algoritmos fornecidos pelas
bibliotecas. O manifesto registra o backend realmente escolhido e sua explicação.

## Experimento reproduzível

Com o ambiente do projeto ativo, a partir da raiz ecoscan:

    python scripts/run_processing_lab.py --output reports/processing_lab

O script cria uma imagem sintética com um retângulo, um pixel de ruído externo
e uma pequena falha interna. Existe máscara de referência conhecida.
Executa todas as operações a partir da **mesma máscara Otsu**, sem alterar o modelo.

Também aceita foto própria autorizada:

    python scripts/run_processing_lab.py --image caminho/objeto.png --kernel-size 5 --kernel-shape cross --output reports/processing_lab_foto

Nesse segundo caso não calcula IoU, porque não existe máscara de referência
anotada. Usa Otsu com seleção automática de polaridade; a interface permite
experimentar também as demais técnicas.

Arquivos principais:

- morphology_overview.png: comparação para apresentação.
- experiment.md e experiment.json: parâmetros e resultados.
- *_mask.png: máscaras binárias sem perdas.
- *_gradient.png: contornos diagnósticos.
- Arquivos de estágios intermediários: sequência efetivamente executada.
- control_pipeline/: original, preparação, máscara e metadados do controle.
- reference_mask.png: referência do exemplo sintético.

No exemplo padrão (quadrado 3×3, uma iteração), o controle tem IoU 0,999442 e a
abertura seguida de fechamento tem IoU 1,0; dois pixels são corrigidos.
Erosão e dilatação isoladas têm IoU menor (0,931641 e 0,934063).
Esse resultado foi construído para ensinar os efeitos das operações.
**Não mede acurácia do EcoScan nem comprova melhoria em fotos reais.**

IoU = pixels da interseção / pixels da união entre referência e máscara prevista.
Mais área, menos ruído aparente ou menos componentes não garantem uma máscara melhor.

## Roteiro para a aula e entrega

1. Apresentar original, dimensão, orientação e representação RGB.
2. Mostrar cinza e histograma; explicar que são representações para análise.
3. Comparar controle e filtro, informando parâmetro e hipótese.
4. Exibir máscara Otsu/HSV/GrabCut e discutir erros de fundo e objeto.
5. Mostrar o kernel e prever o efeito antes de executar dilatação/erosão.
6. Comparar abertura/fechamento e suas etapas intermediárias.
7. Identificar pixels alterados e componentes que foram unidos ou removidos.
8. Comparar a prévia segmentada à entrada RGB preservada que realmente segue para reconhecimento.
9. Separar conclusão sobre qualidade da máscara da conclusão sobre classificação.
10. Entregar parâmetros, imagens, resultados, limitações e fontes usadas.

Para avaliar imagens reais, incluir objeto tocando a borda, dois objetos próximos,
detalhes finos, ruído, reflexo, sombra e objeto transparente. Comparar com máscaras
anotadas e medir IoU/Dice quando houver referência. Separar por objeto/cena nos
conjuntos de avaliação. Não escolher parâmetros somente para uma foto favorável.

## Validação automatizada

    python -m pytest -q tests/test_processing_academic.py tests/test_processing_evidence.py tests/test_morphology.py tests/test_processing_lab.py tests/test_pipeline.py tests/test_image_processing.py tests/test_streamlit_camera_flow.py

Os testes verificam resultados pixel a pixel em formas conhecidas, máscaras
vazias/cheias, bordas, iterações, parâmetros inválidos, preservação do original,
equivalência ao OpenCV usando o mesmo kernel e borda explícita, integração com o
classificador, exportação PNG, troca de parâmetros e acesso ao laboratório público.

O registro histórico de 27/09/2026 relata 243 execuções sem falhas, com arquivos
locais em `reports/` que não acompanham o Git. Para a situação **atual**,
use os resultados da execução do GitHub Actions associada ao commit avaliado.
Esses testes sustentam o comportamento implementado; não substituem a
avaliação independente da segmentação e do reconhecimento em campo.

## Fontes e código

- [Morfologia no OpenCV](https://docs.opencv.org/4.x/d9/d61/tutorial_py_morphological_ops.html).
- [Limiarização e Otsu no OpenCV](https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html).
- Implementação: src/ecoscan/segmentation/morphology.py.
- Integração: src/ecoscan/app/pipeline.py.
- Interface: src/ecoscan/ui/processing_lab.py.
- Experimento: scripts/run_processing_lab.py.

## Relatório acadêmico e gate de fotos reais

O [relatório de entrega PDI](relatorio_pdi_aps.md) registra o estado verificável e
o protocolo para completar figuras/interpretação. Nesta etapa não foram fornecidas
fotos reais autorizadas. Os testes sintéticos validam exportação e cálculos;
não preenchem os dois exemplos reais nem o fracasso diagnosticado exigidos.
