# Controle de entrega e validacao

## Metodo de trabalho

Gestao incremental com backlog priorizado por risco e marcos de aceite.
Uma etapa passa de planejada para implementada, validada localmente e aceita no
ambiente publicado. Esses estados nao sao equivalentes. Nao se usa porcentagem
de arquivos existentes como porcentagem de produto concluido.

Limite de trabalho em andamento: uma entrega estrutural por vez. Cada entrega
tem problema, responsavel por papel, criterio de saida, teste de regressao e
procedimento de retorno. Pessoas e datas devem ser combinadas pelo grupo;
os papeis abaixo nao representam atribuicoes pessoais ja aceitas.

## Quadro de prioridades

| Marco | Prioridade / papel | Entrega e dependencia | Criterio de saida | Situacao |
| --- | --- | --- | --- | --- |
| M1 | P0 / desenvolvimento | Controle de qualidade e diagnostico coerente | Suite aprovada, selecao de modelo consistente, comando estrito bloqueia pendencias, CI executada em clone limpo | Implementado; validado localmente; CI remota a conferir |
| M2 | P0 / backend e infraestrutura | Campanhas e denuncias compartilhadas, apos M1 | Migracao aditiva, autorizacao no servidor, revisoes atomicas com versao, evidencias privadas; sem perda ao reiniciar nem fallback local silencioso | Proxima entrega |
| M3 | P0 / QA e analistas | Aceite entre contas, apos M2 | P01-P12 do plano executados; duas contas e um analista; autor recebe resposta, outra conta nao acessa; reenvio nao duplica | Preparado, aguarda execucao real |
| M4 | P1 / dados e modelagem | Candidato de reconhecimento compativel | Curadoria com origem, separacao por objeto/cena, teste independente, metricas por classe, criterios definidos antes de avaliar, promocao revisada | Pendente; nao retreinado nesta etapa |
| M5 | P1 / mantenedor e coordenacao | Entrega operacional, apos M3/M4 | Backup restaurado em ambiente isolado, retorno de versao ensaiado, retencao e suporte definidos, documentacao e demonstracao aceitas | Pendente |

Mapa e educacao permanecem no escopo. A base de coleta precisa de verificacao de
aceitacao por material e coordenadas antes de prometer proximidade. A camera Live
e um servico separado: o aceite do Streamlit nao comprova sua publicacao.

## M1: alteracoes verificaveis

- Diagnostico escolhe o mesmo artefato que a analise: Keras, visual supervisionado,
  KNN, baseline, conforme disponibilidade. Um teste cobre coexistencia de modelos.
- Aceite identifica evidencia automatizada, inspecao estatica, verificacao nao
  executada e validacao manual necessaria. Registra versao e commit disponiveis.
- Todos os codigos QA-01 a QA-21 aparecem mesmo quando falta uma imagem ou modelo.
- Existencia de perfis de demonstracao nao comprova autorizacao no Supabase.
- Existencia de um arquivo de modelo nao comprova qualidade ou promocao aprovada.
- Inventarios de conclusao nao declaram campanhas/denuncias locais prontas para
  operacao compartilhada. O score antigo e estrutural, nao percentual de entrega.
- GitHub Actions preparado para Python 3.12, instalacao das dependencias, suite,
  diagnostico e artefatos tecnicos por commit, sem segredos de producao.

O workflow segue o padrao de [testes Python do GitHub Actions](https://docs.github.com/en/actions/tutorials/build-and-test-code/python).
Nao instala dependencias de treino opcionais. Nao faz deploy, nao treina modelos
e nao altera o banco. Seus relatorios ficam por 14 dias. O arquivo de dependencias
resolvidas documenta aquela execucao; ainda nao e um lockfile multiplataforma.
CI verde nao e aceite final, nem bloqueia automaticamente o deploy do Streamlit.
Protecao de branch e aprovacao obrigatoria ainda precisam ser configuradas pelo mantenedor.

## Como executar a validacao

Com o ambiente do README instalado:

```bash
python -m unittest discover -s tests -v
python scripts/run_acceptance_checks.py --diagnostic --output reports/diagnostico
python scripts/run_acceptance_checks.py --output reports/acceptance_checks
git diff --check
```

O primeiro comando executa regressao de software. O segundo e um diagnostico
explicito para desenvolvimento. O terceiro e estrito e retorna:

| Codigo de saida | Significado |
| --- | --- |
| 0 | Todos os itens presentes e OK; no modo diagnostico significa apenas ausencia de falhas detectadas |
| 1 | Falha de verificacao, status desconhecido ou erro de execucao |
| 2 | Aceite incompleto: pendencia, atencao, verificacao ausente ou duplicada |

O comando considera os itens, nao apenas os contadores do resumo. Sem
`--sample-image`, busca uma foto em `data/raw`; sem foto, inferencia, pipeline e
frame ficam pendentes. Nao copie fotos pessoais para o Git apenas para passar CI.
Relatorios de uma foto real podem conter caminhos e evidencias: mantenha-os privados.

QA-09 e QA-18 a QA-21 sao deliberadamente pendentes no diagnostico local. Este
script nao acessa contas reais nem importa um aceite humano automaticamente.
A evidencia externa deve ser executada e revisada no registro abaixo. Uma etapa
futura podera incorporar esse registro ao comando com validacao de versao;
na implementacao atual, nao edite o JSON nem desative verificacoes para obter verde.

## Registro desta rodada

Em 03/10/2026, na copia de publicacao:

- Antes das alteracoes: 281 testes aprovados.
- Apos as alteracoes: 291 testes aprovados; `git diff --check` sem erros.
- Diagnostico sem foto de amostra: 10 OK, 3 atencoes, 8 pendencias, zero falhas.
- Atencoes: cobertura de coleta, dataset ausente nesta copia e marcadores de
  interface que ainda exigem teste funcional. Nao significam 3 bugs comprovados.
- Pendencias: smoke test de inferencia/pipeline/frame, aceite do modelo e os
  quatro marcos externos. Dataset ausente neste clone nao significa que o grupo
  nao possua fotos em outro local ou no Storage.
- Convites dos tres analistas entregues segundo os logs do Brevo. Entrega de
  email nao comprova que criaram conta, confirmaram cadastro ou testaram o app.

Os artefatos locais ficam em `reports/acceptance_checks`, fora do Git. O commit
registrado antes do commit desta entrega identifica a base; mudancas locais
devem ser conferidas no diff. Reexecutar apos a publicacao para registrar a revisao final.

Continuacao em 04/10/2026: a primeira CI instalou Python 3.12 e executou os
291 testes, identificando uma incompatibilidade do teste visual com o tipo
`image` do AppTest no Streamlit 1.65 (a versao local 1.57 usava `imgs`). O teste
foi ajustado para ambos e agora verifica tambem as URLs de cada imagem. Nao foi
removida a verificacao do antes/depois. Os sete testes de evidencias passaram
na versao 1.57, e a suite completa de 291 passou localmente com a 1.65 isolada.
A primeira publicacao foi conferida no Perfil do app, revisao `0c66a2e37ab9`.
O resultado da nova CI deve ser conferido antes de encerrar M1.

## Preparacao da proxima entrega (M2)

1. Inventariar campanhas e denuncias atuais sem enviar dados privados ao Git.
2. Criar migracao aditiva separando campanha publicada, relato e revisao.
3. Manter identidade verificada no servidor; visitante nao grava; analista
   revisa; participante consulta somente seus registros privados.
4. Tornar submissao idempotente e revisao condicional a versao esperada. Duas
   revisoes simultaneas nao podem sobrescrever uma a outra silenciosamente.
5. Ativar somente apos teste de migracao, permissao e reinicio; uma falha remota
   deve informar indisponibilidade, nunca apresentar sucesso ou lista vazia falsos.
6. Preservar originais e dados anteriores; rollback do codigo nao deve apagar banco.

Nao ha nova migracao aplicada em producao nesta rodada.

## Riscos e resposta

| Risco | Resposta / evidencia exigida |
| --- | --- |
| Perda de campanha ou denuncia em reinicio | M2; teste de leitura apos reinicio em outra sessao |
| Mistura de contas ou permissao indevida | P01-P10; falha bloqueia o piloto, sem excecao informal |
| Imagem errada entrar no treino | Revisao humana, origem e grupos de objeto/cena; treino separado da aprovacao |
| Metricas melhorarem apenas no treino | Criterios previos e conjunto independente; comparacao por classe |
| Modelo/preparo divergirem | Publicar artefato e contrato juntos; conservar anterior |
| Envio de email sem cadastro concluido | Distinguir entregue, confirmado e login; nao criar senhas compartilhadas |

## Registro de aceite externo

Preencher em ambiente privado para cada P01-P12 e marco; publicar somente resumo
sem emails, tokens, fotos ou protocolos identificaveis:

| Caso / marco | Commit | Ambiente / dispositivo | Papel executor | Esperado / observado | Evidencia privada | Resultado / defeito |
| --- | --- | --- | --- | --- | --- | --- |
| A preencher | | | | | | |

Uma entrega so encerra quando possui evidencia, revisao por outro integrante,
documentacao coerente, ausencia de defeitos bloqueadores e retorno ensaiado.
Nao afirmar aumento de acuracia, impacto ambiental medido ou aceite institucional
com base apenas na aprovacao dos testes de software.
