# Rodada de reconhecimento de 16/10/2026

## Resultado executado

Foi treinado um candidato MobileNetV2 com caracteristicas congeladas e regressao
logistica. Fonte: seis pastas locais previamente curadas; 723 imagens, agrupadas
em 720 grupos automaticos. Foram usadas 433 para treino, 145 para validacao e
145 para teste. Nao havia identificadores de objeto/sessao de captura; essa
limitacao permanece mesmo com copias exatas e proximas agrupadas.

O modelo foi selecionado pela validacao (`C=0.1`, macro-F1 62,95%). O limiar
de 0,95 e o fallback conservador: a meta de 90% de acerto entre respostas
aceitas **nao foi atingida na validacao** (35/43, 81,4%). Nao publicar esse
limiar como promessa de seguranca.

| Medida no teste | Resultado |
| --- | ---: |
| Acuracia top-1 | 56,6% |
| Macro-F1 | 57,6% |
| Respostas aceitas | 36/145 (24,8%) |
| Acerto entre respostas aceitas | 32/36 (88,9%) |
| Baseline antigo nos mesmos pixels, top-1 | 39,3% |

O baseline pode ter usado essas imagens em rodadas anteriores; a comparacao
e diagnostica, nao uma estimativa independente do ganho em campo. O candidato
tambem erra com escores altos. Fotos novas de participantes sao necessarias
antes de integrar e promover esse modelo no aplicativo.

## Resultado por classe

| Classe | Precisao | Recall | F1 | Fotos de teste |
| --- | ---: | ---: | ---: | ---: |
| Pilhas/baterias | 62,5% | 66,7% | 64,5% | 15 |
| Pequenos eletronicos | 71,4% | 66,7% | 69,0% | 15 |
| Vidro | 54,2% | 44,8% | 49,1% | 29 |
| Metal | 56,4% | 75,9% | 64,7% | 29 |
| Papel/papelao | 59,3% | 55,2% | 57,1% | 29 |
| Plastico | 44,0% | 39,3% | 41,5% | 28 |

Prioridade de coleta/revisao: plastico e vidro, e contraste entre latas altas,
pilhas e garrafas. A melhoria agregada nao equivale a melhoria de todas as
classes; plastico apresentou F1 inferior ao baseline nessa comparacao.

## Casos de regressao fornecidos pelo usuario

As tres fotos foram avaliadas depois do treino e nao foram adicionadas a ele.
Nenhuma teve hash original identico ao manifesto; isso nao exclui copias
visualmente semelhantes nem demonstra independencia completa.

| Caso | Hipotese do candidato | Escore | Aceito |
| --- | --- | ---: | --- |
| Grupo de garrafas PET | Vidro | 81,8% | Nao |
| Lata vermelha de catalogo | Metal | 65,5% | Nao |
| Lata alta de energetico em sala | Pilha/bateria | 59,5% | Nao |

Nao foi feito ajuste para decorar essas fotos. Elas formam uma bateria de
regressao conhecida; uma futura avaliacao final precisa de outros objetos.

## Revisao dos dados

Inspecoes pontuais confirmaram uma embalagem plastica bastante deformada e uma
cena com garrafa de vidro, espelho e papel. Sao casos reais de dificuldade,
nao evidencias suficientes para alterar os rotulos automaticamente. Preservar
originais; o analista deve decidir se o objeto principal esta claro e se a
imagem representa o escopo. Nomes de arquivo sozinhos nao validam materiais.

Para a proxima rodada:

1. Registrar objeto e sessao em `capture_groups.csv`, mantendo todos os angulos
   do mesmo objeto juntos.
2. Priorizar garrafas PET transparentes/coloridas/amassadas, latas comuns e altas,
   latas amassadas e garrafas de vidro; variar fundo e iluminacao.
3. Conferir material e objeto principal nas imagens de cenas amplas ou misturadas.
4. Incorporar apenas reportes consentidos aprovados pela secretaria.
5. Reservar um novo lote cego de fotos, que nao participa de ajustes.

## Artefatos e estado da entrega

Rodada local preservada em `reports/training_mobilenet_20261016/`: modelo,
backbone, manifesto, predicoes, metricas e checkpoints. Imagens e pesos nao
foram enviados ao GitHub nesta rodada. O procedimento e o codigo ficam
versionados para a equipe.

SHA-256 do candidato:
`aeadd74e0857361cab2a64cc4ddc4e8dd06a9a890cb27fe0c50fa7eb3be05b05`.

SHA-256 do manifesto:
`d4a3715cf07b21f1897d1478a040da05760b8c9243fcca5caf12dd12101b72f0`.

O reconhecimento publico permanece com o modelo anterior. Esse candidato
nao passou pelo aceite de promocao e nao deve orientar descarte automaticamente.
Consulte o [procedimento reproduzivel](treinamento_mobilenet.md).
