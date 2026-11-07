# Prática de processamento digital de imagens

O EcoScan permite demonstrar o tratamento da imagem antes do reconhecimento.
Este roteiro conecta conceitos usuais da disciplina à implementação e às
evidências. Conferir com o professor a lista e o formato específicos da avaliação;
a ementa oficial não foi fornecida.

## Como acessar

- Visitante/participante: expandir **Laboratório de processamento de imagens** na
  página principal. Selecionar os parâmetros e tirar/enviar a foto em Escanear.
  O resultado exibe **Processamento aplicado: processamento experimental**, sem exigir abrir a área técnica.
  As abas apresentam o antes/depois e a diferença de cada operação.
  **Baixar evidências do processamento (ZIP)** salva as imagens PNG e o manifesto de parâmetros.
- Analista: usar os **Parâmetros técnicos** na barra lateral e a aba **Processamento**.
- Mudar uma operação ou parâmetro reprocessa a foto carregada; não é necessário
  reenviar uma contribuição à secretaria. A entrada oficial do reconhecedor permanece fixa.
- Para demonstrar sem login, modelo treinado ou banco: executar o experimento
  sintético descrito abaixo.

## Sequência real do pipeline

    Trilha diagnostic_processing (experimento):
    Arquivo validado e orientação EXIF corrigida
      → conversão RGB e transparência sobre branco
      → redução proporcional por área (lado maior até 640 px)
      → diagnóstico e filtragem
      → segmentação (máscara binária)
      → abertura + fechamento da máscara (padrão ativo)
      → máscara aplicada somente à prévia diagnóstica
      → componentes, área e caixas

    Trilha independente recognition_preparation:
    RGB orientado → redução proporcional → filtro do perfil oficial auto
      → RGB completo com margens para o classificador (224×224)
      → reconhecimento assistido e confirmação humana

A imagem original é preservada em memória. A máscara bruta e a máscara tratada
são mantidas separadamente. O padrão seleciona **filtragem e segmentação
adaptativas → abertura + fechamento**, com elemento quadrado 3×3, uma iteração
por primitiva e borda zero. Para demonstrar especificamente mediana 3×3 e Otsu,
selecione esses métodos no laboratório.
A máscara tratada não apaga pixels da entrada de reconhecimento. A versão
[RGB preservado v2](processamento_preservado_v2.md) mantém cor e proporções.
O perfil oficial é configurado em config/settings.json e deve coincidir com o contrato
de models/semantic-v1/semantic.json, inclusive o SHA-256 do perfil. O avaliador e o
treinamento de novas contribuições também usam esses padrões. O serviço recusa um
contrato incompatível antes de chamar o encoder. O manifesto inclui as duas trilhas
e o SHA-256 dos bytes C-order do RGB oficial, além dos hashes shape/dtype já existentes.
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
| Avaliação | IoU em máscara sintética conhecida; comparação controlada | Relatório e prancha do experimento |

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
e às medições. O classificador recebe o RGB filtrado pelo perfil oficial e redimensionado, **sem
aplicação da máscara**. Os filtros escolhidos no laboratório pertencem à trilha
`diagnostic_processing` e não alteram `recognition_preparation`. Os testes verificam a preservação dos pixels do objeto
e a correspondência das evidências exportadas com as operações executadas.

- Antes/depois de redimensionamento, filtro, segmentação, cada primitiva e aplicação da máscara.
- Diferença absoluta por pixel (máximo entre canais RGB), sem amplificação artificial.
- Pixels alterados, kernel, ordem, iterações e parâmetros efetivamente usados.
- Operação executada sem mudança é identificada como tal; controle desativado tem estado distinto.
- Em dimensões/representações distintas não se calcula diferença pixel a pixel.
- ZIP em memória por análise: PNGs sem perdas, prancha e manifesto com hashes de conteúdo.
  O manifesto do ZIP não inclui caminhos do servidor nem identidade da conta.

A prancha de antes/depois demonstra operações, não acurácia do classificador.
O caminho de imagem abaixo é um **exemplo de um conjunto local não versionado**;
substitua-o por uma foto autorizada que realmente exista no seu computador.
Os relatórios gerados na pasta `reports/` não são distribuídos pelo Git.

Para reproduzir (na raiz do projeto):

    python scripts/export_processing_evidence.py --image data/test/metal/metal_0011_burn-wv-deckel_processed.png --output reports/evidencia_foto

O comando usa o mesmo pipeline e salva também JSON e ZIP. Aceita uma foto autorizada
em --image. Os arquivos de evidência contêm a foto: compartilhar apenas os autorizados.

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
8. Comparar o processamento experimental à preparação para reconhecimento exibida separadamente.
9. Separar conclusão sobre qualidade da máscara da conclusão sobre classificação.
10. Entregar parâmetros, imagens, resultados, limitações e fontes usadas.

Para avaliar imagens reais, incluir objeto tocando a borda, dois objetos próximos,
detalhes finos, ruído, reflexo, sombra e objeto transparente. Comparar com máscaras
anotadas e medir IoU/Dice quando houver referência. Separar por objeto/cena nos
conjuntos de avaliação. Não escolher parâmetros somente para uma foto favorável.

## Validação automatizada

Separação das trilhas (mudança de 07/11/2026, baseline `89622ec714b815c216a9215ab9ba69999b39c6b8`):

    python -m pytest tests/test_processing_tracks.py -q

Antes da alteração, as sete escolhas de filtro sondadas não preservavam a entrada
ou o contrato padrão; o encoder era chamado antes de rejeitar um contrato incompatível.
Os testes agora verificam invariância exata, efeito didático visível, EXIF/RGB/margens,
hashes, contrato da release, gate de qualidade estável, manifesto e rerun de controles
Streamlit. `ModelLoadError` interrompe contratos incompatíveis antes da predição,
usando o tratamento público de erros já existente. Os atributos anteriores do resultado
continuam disponíveis; `diagnostic_processing` e `recognition_preparation` nomeiam as trilhas.

O smoke sintético com CPU ONNX real confirmou scores idênticos entre filtro padrão e
experimento gaussiano, sem alterar artefato, limiar ou confirmação obrigatória. Isso
comprova o contrato de software, não acurácia de campo. O RGB oficial padrão também
foi comparado pixel a pixel ao pipeline da baseline, sem diferença na cena usada.

    python -m unittest tests.test_processing_evidence tests.test_morphology tests.test_processing_lab tests.test_pipeline tests.test_image_processing tests.test_streamlit_camera_flow -v

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
