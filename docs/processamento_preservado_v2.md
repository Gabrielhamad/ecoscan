# Preparacao de imagens: RGB preservado v2

[Projeto](../README.md) | [Treinamento](treinamento_reconhecimento.md)

Revisao: 29/09/2026. Contrato: `rgb-preserved-v2`.

## Decisao de engenharia

A versao anterior reduzia toda foto diretamente a um quadrado e aplicava a
mascara antes da classificacao. Nos exemplos auditados, a selecao por saturacao
podia manter a tinta de uma lata e remover a tampa e a base metalicas. O filtro
automatico tambem podia confundir textura com ruido e clarear fundos ja claros.

Agora a preparacao preserva proporcoes, cor e a foto inteira. Filtrar e uma
decisao condicional: se o ganho nao passar pelos limites de preservacao, a
imagem permanece sem filtro. Segmentacao e morfologia continuam executadas e
visiveis antes do reconhecimento, mas nao apagam pixels da entrada do modelo.

```text
Arquivo -> EXIF/RGB -> reducao proporcional -> diagnostico -> correcao ou controle
                                                        |
                +---------------------------------------+
                |                                       |
       RGB completo + margens                  Otsu/GrabCut ou abstencao
                |                                       |
       atributos e classificacao               morfologia, regioes, overlay
                |                                       |
       hipotese + verificacoes                  evidencias para inspecao
```

## Tecnicas e aplicacao

| Tecnica | Quando e como e usada | Limite importante |
| --- | --- | --- |
| Orientacao EXIF e RGB | Corrige orientacao e compoe transparencia sobre branco | Nao recupera detalhes ausentes |
| Interpolacao por area | Limita o lado maior a 640 px sem distorcer ou ampliar | A reducao ainda perde resolucao |
| Diagnostico | Percentis 5/95, estimativa wavelet de ruido e pixels extremos isolados | Texturas naturais ainda podem enganar estimadores |
| Mediana seletiva | Janela 3x3 somente nos pixels diagnosticados como impulsivos | Nao altera os pixels fora dessa selecao |
| Gaussiano | Candidato para ruido estimado, janela 3x3, sigma 0,55 | Pode borrar bordas; precisa passar pelos limites |
| Bilateral | Candidato alternativo para ruido, intensidade limitada | Preservar bordas nao garante preservar textura |
| CLAHE em luminancia | Faixa tonal reduzida, ruido baixo, clip 1,5 e mistura de 20% | Pode amplificar ruido ou clarear demais; ha controle |
| Otsu | Mascara auxiliar de intensidade com polaridade estimada pela borda | Nao reconhece material e falha em fundos complexos |
| GrabCut | Mascara auxiliar RGB inicializada por retangulo, 3 iteracoes | Objeto cortado pela margem pode ser excluido |
| HSV | Experimento manual de saturacao/brilho | Nao e padrao automatico: pode excluir metal prateado |
| Morfologia | Abertura/fechamento da mascara, kernel 3x3; primitivas exportadas | Pode remover partes pequenas ou unir regioes |
| Sobel e Canny | Demonstracao manual de bordas | Nao substituem o RGB na classificacao |
| Letterbox | Ajusta a foto inteira ao alvo 224x224, com margens cinza 127 | O classificador ainda extrai/normaliza atributos internamente |

Referencias tecnicas: [filtros OpenCV](https://docs.opencv.org/4.13.0/d4/d13/tutorial_py_filtering.html),
[CLAHE](https://docs.opencv.org/4.13.0/d5/daf/tutorial_py_histogram_equalization.html),
[GrabCut](https://docs.opencv.org/4.13.0/d8/d83/tutorial_py_grabcut.html) e
[transformacoes geometricas](https://docs.opencv.org/4.13.0/da/d54/group__imgproc__transform.html).
Os limiares do EcoScan abaixo sao escolhas do projeto, nao recomendacoes universais dessas fontes.

## Criterios automaticos

O controle sem filtro participa de toda analise. A politica aplica no maximo
uma correcao, evitando encadear alteracoes que escondam sua origem:

- Ruido impulsivo: fracao minima 0,0005; exige reducao de pelo menos 50% e
  preservacao exata fora dos pixels diagnosticados.
- Ruido estimado: sigma minimo 4 em escala 0-255; exige reducao estimada de 15%.
- Contraste: amplitude entre percentis maior que 8 e menor que 70, com sigma
  de ruido abaixo de 6; exige ganho de amplitude de 4%.
- Preservacao geral: variacao cromatica media Lab ate 3, alteracao media RGB
  ate 10 e aumento de saturacao de extremos ate 0,005.
- Para Gaussiano, bilateral e CLAHE: SSIM contra a entrada pelo menos 0,82 e
  retencao de bordas fortes de pelo menos 0,85. A mediana seletiva usa a
  preservacao exata fora dos impulsos em lugar deste criterio espacial.

A SSIM contra uma foto ruidosa mede semelhanca, nao qualidade verdadeira.
Por isso o teste controlado usa uma referencia limpa conhecida. Veja
[metricas do scikit-image](https://scikit-image.org/docs/stable/api/skimage.metrics.html)
e [exemplos de reducao de ruido](https://scikit-image.org/docs/stable/auto_examples/filters/plot_denoise.html).
Um score interno nao comprova aumento de acuracia do classificador.

Se nenhuma mascara candidata for geometricamente plausivel, a segmentacao
retorna sem primeiro plano confiavel, em vez de inventar um objeto. Caixas e
mapa visual representam componentes da mascara, nao deteccoes semanticas,
temperatura ou explicacao Grad-CAM.

## Evidencias reproduziveis

Na raiz do repositorio, com as dependencias instaladas:

```bash
python scripts/audit_preprocessing.py --synthetic --output reports/preprocessing_audit/synthetic
python scripts/audit_preprocessing.py --output reports/preprocessing_audit/manual caminho/foto.jpg
python -m unittest discover -s tests
```

Sem caminhos, a auditoria seleciona a primeira imagem disponivel de cada classe
em `data/curated`. O script produz pranchas e JSON locais; nao treina, nao envia
fotos e nao modifica os originais. A auditoria real registra latencia local,
parametros, dimensoes e decisoes, mas nao calcula acuracia sem rotulos.

Resultado controlado em 29/09/2026, referencia geometrica RGB 160x160, seed 42:

| Entrada | Correcao | MSE antes -> depois | PSNR antes -> depois | SSIM com referencia antes -> depois |
| --- | --- | --- | --- | --- |
| Limpa | Nenhuma | 0 -> 0 | Infinito, sem erro | 1 -> 1 |
| Impulsos brancos em 1,5% dos pixels | Mediana seletiva | 180,18 -> 1,52 | 25,57 -> 46,32 dB | 0,674 -> 0,995 |
| Ruido Gaussiano sigma 9 | Gaussiano | 81,76 -> 33,34 | 29,01 -> 32,90 dB | 0,482 -> 0,728 |

Estes tres cenarios sao pequenos testes de regressao, nao um benchmark de fotos
reais. Na auditoria dos tres exemplos reportados pelo usuario, o modo automatico
preservou o RGB sem filtro; a entrada do classificador manteve a foto completa,
inclusive tampa e base das latas. As fotos pessoais e a imagem com marca-d'agua
ficaram fora do Git e nao foram incorporadas ao treino nesta alteracao.

## Compatibilidade com o modelo

Preparar melhor a entrada muda a distribuicao de atributos. O modelo antigo
foi treinado com imagens diferentes e nao pode ser anunciado como validado
para esta versao. Ele pode produzir uma hipotese provisoria, mas o servico
marca a resposta como nao aceita quando faltar compatibilidade.

O contrato inclui versao, dimensoes, margens, configuracao de filtros e o hash
do artefato. A preparacao grava `processing_contract.json`; o ciclo de treino
grava `<modelo>.processing.json`. A inferencia compara ambos. Esse arquivo e
evidencia de compatibilidade de preparacao, nao certificacao de precisao.
Nao crie um contrato artificial para liberar o modelo antigo.

O proximo treino deve partir dos originais curados, nunca das antigas imagens
mascaradas. Use o [ciclo controlado](treinamento_reconhecimento.md), avalie fotos
independentes e promova o modelo e seu contrato juntos apenas apos revisao.
Scripts isolados de treinamento experimental nao certificam esse contrato.
Nenhum novo modelo foi treinado nem promovido nesta revisao.

## Roteiro do grupo

1. Abrir Escanear, enviar uma foto e conferir antes/depois e o motivo da decisao.
2. Conferir cor, formato, tampa, base, rotulo e detalhes; filtros nao precisam
   alterar uma foto que ja esta boa.
3. Inspecionar a mascara separadamente: uma mascara ruim nao pode apagar o RGB.
4. Em caso de hipotese errada, reportar com consentimento e categoria correta;
   enquanto o novo modelo nao estiver validado, consultar Descarte manualmente.
5. A secretaria revisa os reportes e o grupo organiza objetos/cenas separados
   para treino e teste. Aprovar um reporte nao retreina o modelo em producao.

O Live reutiliza o servico de analise e a mesma protecao de compatibilidade,
mas e um servidor separado do Streamlit e ainda precisa de medicao de latencia
e estabilidade em dispositivos reais. Este trabalho nao o publica na nuvem.
