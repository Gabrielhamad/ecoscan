# EcoScan: roteiro tecnico de estudos e entregas do grupo

## Objetivo e organizacao

Transformar o sistema desenvolvido em conhecimento compartilhado: cada integrante
precisa explicar sua parte, demonstrar uma evidencia e contribuir com o relatorio.
Gabriel permanece responsavel pelo desenvolvimento e pela integracao. Os demais
nao precisam programar para entregar as atividades propostas.

Esta divisao e uma sugestao operacional para Antonio, Guilherme e Gustavo;
os temas podem ser trocados conforme a disponibilidade. O cronograma usa dias
relativos ao inicio combinado pelo grupo, sem presumir a data de entrega da APS.

## Base comum: todos leem no primeiro dia

- [Guia do grupo](guia_do_grupo.md): proposta, funcionamento e demonstracao.
- [Escopo de objetos](escopo_objetos_v1.md): alvos de coleta e avaliacao.
- [Arquitetura](arquitetura_atual.md): componentes e responsabilidades.
- [Validacao das jornadas](validacao_jornadas.md): testes e pendencias reais.

O EcoScan simula uma secretaria ambiental promovendo educacao e orientacao
de descarte em Sao Paulo. O fluxo e: captura -> validacao e preparo ->
reconhecimento -> orientacao -> contribuicao consentida -> revisao da secretaria
-> curadoria -> treinamento e avaliacao de candidato -> decisao de publicacao.

O classificador trabalha com seis materiais: plastico, metal, papel/papelao,
vidro, pilhas e eletronicos. A coleta contempla 12 tipos de objeto definidos no
escopo. Oleo e medicamentos possuem orientacao manual; organicos ficam fora
do reconhecimento inicial. Uma correcao aprovada entra na fila de aprendizado;
isso nao altera automaticamente o modelo publicado.

## Antonio: preparo, filtros e convolucao

**Pergunta central:** como preparar uma foto preservando informacoes importantes?

Estudar orientacao EXIF, RGB, redimensionamento proporcional, letterbox,
ruido impulsivo e gaussiano, filtro de mediana, bilateral, gaussiano e CLAHE.
Entender kernel, sigma e tratamento das bordas. Explicar que gaussiano e
convolucao com pesos definidos; filtros de CNN possuem pesos aprendidos.
Mediana e bilateral nao devem ser apresentados como convolucoes lineares.

Material interno:

- [Preparo e convolucao](preparo_e_convolucao.md).
- `src/ecoscan/image_processing/preprocessing.py`.
- `src/ecoscan/image_processing/filters.py`.
- `src/ecoscan/image_processing/adaptive_filters.py`.
- `src/ecoscan/app/pipeline.py`.

Pesquisa externa: livro de processamento digital de imagens e documentacao
oficial do OpenCV para filtros e CLAHE. Registrar autor/instituicao, titulo,
edicao ou versao, ano quando disponivel, URL e data de acesso.

Entregar:

- Texto de 2 a 3 paginas com conceito, aplicacao no EcoScan e justificativa.
- Quadro: tecnica, problema tratado, parametros, vantagem e cuidado.
- Tres comparacoes antes/depois das evidencias do projeto, identificando
  tecnica e parametros; incluir um caso de preservacao sem filtro ou de piora.
- Explicacao oral de 3 minutos, incluindo um kernel gaussiano.

Aceite: explicar por que filtrar todas as fotos da mesma maneira pode piorar
o resultado e por que suavizacao nao recupera detalhes de uma foto desfocada.
Relacionar qualidade visual e reconhecimento sem presumir que sao equivalentes.

## Guilherme: segmentacao, dataset e reconhecimento

**Pergunta central:** como localizar regioes e avaliar se o material foi reconhecido?

Estudar Otsu, GrabCut, mascaras, contornos, Sobel/Canny e morfologia:
erosao, dilatacao, abertura e fechamento. Diferenciar objeto segmentado de
classe reconhecida. No preparo atual, a mascara serve a inspecao; o
classificador recebe a imagem RGB preparada, sem fundo apagado pela mascara.

Estudar rotulagem, variacoes de angulo/luz/deformacao, separacao por objeto
fisico ou sessao, treino/validacao/teste, duplicatas e vazamento de dados.
Entender CNN, transferencia de aprendizado e diferenca entre extrator de
caracteristicas e fine-tuning. Explicar matriz de confusao, precisao, recall,
F1, cobertura e rejeicao de casos incertos.

Material interno:

- [Segmentacao adaptativa](segmentacao_adaptativa.md).
- [Escopo](escopo_objetos_v1.md).
- [Dataset revisado](dataset_corrigido_v1.md).
- [Treinamento MobileNet](treinamento_mobilenet.md).
- `src/ecoscan/segmentation/` e `src/ecoscan/classification/`.

Pesquisa externa: livro de visao/processamento de imagens e fontes primarias
das arquiteturas e bibliotecas efetivamente discutidas. Identificar quais
modelos sao experimentais e qual modelo esta ativo antes de descreve-los.

Entregar:

- Texto de 3 a 4 paginas separando segmentacao, preparacao dos dados e reconhecimento.
- Uma figura com original, mascara e contornos, com metodo identificado.
- Uma matriz de confusao ja gerada pelo projeto, com interpretacao de dois erros.
- Checklist de coleta por objeto e variacoes, sem repetir imagens entre conjuntos.
- Explicacao oral de 4 minutos sobre o percurso de uma foto ate o resultado.

Aceite: nao chamar caixas/contornos de deteccao supervisionada de cada objeto;
nao apresentar desempenho de candidato como desempenho do sistema publicado.
Consultar Gabriel sobre a versao ativa antes de fechar o texto.

## Gustavo: educacao ambiental, missoes e validacao de uso

**Pergunta central:** como o aplicativo orienta e incentiva uma mudanca de comportamento?

Estudar impactos do descarte incorreto, separacao adequada, possibilidades de
reciclagem e restricoes de recebimento. Cobrir os seis materiais e a orientacao
manual de oleo e medicamentos. Para Sao Paulo, consultar fontes oficiais dos
operadores e da Prefeitura; nao presumir que todo ecoponto aceita pilhas,
eletronicos ou residuos especiais.

Explicar participante, visitante e analista; campanhas, missoes, pontos e
recompensas digitais. Diferenciar foto de reconhecimento de comprovante de
entrega fisica. Beneficios materiais ou publicos dependem de acordo real e
nao devem aparecer como concedidos pelo piloto.

Material interno:

- [Campanhas e relatos](campanhas_e_relatos.md).
- [Validacao de jornadas](validacao_jornadas.md).
- `src/ecoscan/ui/education.py` e `src/ecoscan/ui/collection_map.py`.
- `src/ecoscan/services/campaigns.py` e `src/ecoscan/services/engagement.py`.

Pesquisa externa: Prefeitura de Sao Paulo, SINIR e orgaos ambientais; estudos
sobre educacao ambiental e incentivos, quando usados para sustentar afirmacoes.
Nao atribuir reducoes de poluicao ou emissao ao aplicativo sem medicao propria.

Entregar:

- Texto de 2 a 3 paginas: problema, motivacao, beneficios pretendidos e recursos educativos.
- Quadro por material: impacto, preparo seguro, destino, possivel reciclagem e fonte.
- Tres propostas de missao: objetivo educativo, acao, evidencia, regra de
  pontuacao unica e medida contra repeticao; Gabriel confere viabilidade.
- Testar cadastro/confirmacao, mapa, desafio e protocolo; registrar aparelho,
  navegador, revisao, esperado e observado, sem senhas ou links privados.
- Explicacao oral de 3 minutos sobre a experiencia do cidadao.

Aceite: orientacoes com fonte e limites locais; testes registrados como
aprovados somente apos execucao. Marcar o que depender de outro integrante.

## Gabriel: integracao, arquitetura e revisao final

Consolidar Python/Streamlit, processamento, reconhecimento, Supabase Auth,
PostgreSQL/Storage, publicacao GitHub/Streamlit e tratamento de erros.
Explicar autorizacao da secretaria, privacidade das fotos, persistencia,
controle de revisao e fluxo de contribuicoes para treinamento.

Entregar diagrama de arquitetura, demonstracao completa, resumo da versao
ativa e quadro de testes com resultados. Revisar os textos dos colegas contra
codigo e evidencias; montar o relatorio e a apresentacao.

## Cronograma sugerido: sete dias

| Etapa | Quando | Entrega e dependencia |
| --- | --- | --- |
| Alinhamento | Dia 1 | Todos leem base comum; Gabriel apresenta fluxo e confirma divisao |
| Estudo dirigido | Dias 2 e 3 | Cada responsavel entrega resumo, fontes e duvidas |
| Evidencias | Dia 4 | Antonio/Guilherme escolhem figuras; Gustavo coordena testes; Gabriel apoia execucao |
| Texto | Dia 5 | Textos e figuras com titulos, fontes e referencias; Gabriel revisa consistencia |
| Integracao | Dia 6 | Conferir chamadas, legenda, ABNT, resultados e versao do sistema |
| Ensaio | Dia 7 | Demonstracao no celular e PC; cada integrante explica sua parte e responde perguntas |

Se a entrega atual for somente a etapa de filtragem do modelo enviado, priorizar
introducao e o material de Antonio, com apoio ambiental de Gustavo. Os demais
conteudos ficam preparados para as etapas seguintes, conforme pedido do professor.

## Padrao de entrega para todos

Entregar texto editavel com: conceito -> uso concreto no EcoScan -> evidencia
-> interpretacao -> referencias. Usar Arial 12 e espacamento 1,5 conforme o
modelo enviado. Preparar referencias e citacoes conforme a orientacao ABNT
adotada pela instituicao. A equipe consolida capa e identificacao uma unica vez
por elemento exigido, sem repetir nomes no corpo de cada contribuicao.

Nao e necessario fixar a quantidade de imagens no texto introdutorio. Ao
discutir resultados, identificar a rodada e a amostra efetivamente avaliadas
para permitir que o leitor entenda e reproduza a evidencia.

## Perguntas que todos devem saber responder

1. Qual problema ambiental o EcoScan procura enfrentar?
2. Qual e a sequencia entre captura, preparo e reconhecimento?
3. Qual a diferenca entre filtragem, segmentacao e classificacao?
4. Quais objetos estao no escopo e como o sistema trata os demais?
5. Como reportes revisados contribuem para um futuro treinamento?
6. O que as missoes incentivam e o que os pontos comprovam?
7. Como distinguimos recurso implementado, teste executado e melhoria planejada?
