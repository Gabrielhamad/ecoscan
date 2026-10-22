# Aprendizado revisado pela secretaria

## Operacao

1. O usuario autenticado envia a foto com consentimento e a categoria sugerida.
2. A secretaria confere o objeto, corrige a categoria e aprova.
3. A contribuicao recebe o estado `queued` no Supabase.
4. O GitHub Actions verifica a fila a cada 15 minutos. O horario pode atrasar
   conforme a disponibilidade do servico; nao se trata de treinamento instantaneo.
5. O executor prepara as imagens pelo mesmo pipeline do aplicativo e extrai
   caracteristicas com o mesmo encoder neural ONNX.
6. A cabeca classificadora e treinada novamente com a base anterior e todas as
   contribuicoes aprovadas. O encoder permanece congelado.
7. O candidato e comparado com o modelo ativo usando a mesma validacao fixa.
8. Quando aprovado, o ponteiro privado `semantic_active.json` e atualizado.
   O aplicativo consulta a versao remota nas proximas analises, com cache de
   ate 60 segundos. Uma analise ja mostrada na tela nao e recalculada sozinha.

## Criterios de publicacao

Para este modo assistido, exige-se aumento superior a 0,005 no macro F1,
nenhuma queda de recall por categoria, pelo menos dez exemplos de validacao
por classe e nenhum aumento no numero de erros acima do limiar de confianca.
Nao se ajustam parametros usando o resultado da validacao nesta rotina.

A validacao e historica e reutilizada: nao representa um teste independente
de campo. Mesmo apos a publicacao, o aplicativo exige confirmacao do material.
Esta rotina nao habilita descarte ou pontuacao automatica por reconhecimento.

## Estados

- Na fila: a aprovacao foi salva e aguarda o executor.
- Treinando: as fotos aprovadas estao sendo preparadas e incorporadas.
- Validando: o candidato esta sendo comparado com a versao anterior.
- Publicado: a contribuicao participou de uma versao promovida.
- Validacao nao aprovada: o modelo anterior continua ativo. A contribuicao
  permanece na base para a proxima rodada com novos exemplos.
- Falha: o executor tentara novamente na proxima execucao.

Uma unica foto pode iniciar uma rodada, mas nao garante melhora generalizavel.
Nao ha exigencia de a secretaria baixar arquivos ou executar treinamento manual.

## Privacidade e rastreabilidade

As fotos de contribuicoes ficam no armazenamento privado e sao processadas
temporariamente no executor. Nao sao adicionadas ao GitHub ou aos artefatos
publicos. A base inicial versionada contem caracteristicas numericas de imagens
publicas revisadas, nao fotos ou reportes pessoais. O conjunto de teste foi
excluido dessa base de aprendizado.

Cada lote registra metricas e artefatos privados. Hashes verificam a base, a
cabeca e os metadados. A revisao e conferida novamente antes da publicacao;
revogar ou alterar uma contribuicao invalida o carregamento da versao afetada.

## Dependencias operacionais

O workflow requer `ECOSCAN_TRAINING_ENABLED=true` nas variaveis do GitHub,
os segredos privados de conexao Supabase existentes e o bucket privado
`ecoscan-training`. O Streamlit precisa da mesma conexao e de modelos remotos
habilitados. A agenda do GitHub pode ser desabilitada apos inatividade do
repositorio; monitorar as execucoes e o consumo da conta.

Testes automatizados cobrem fila vazia, inclusao de foto aprovada, bloqueio de
regressao, publicacao condicional e integridade dos artefatos. Confirmar a primeira
execucao no ambiente publicado antes de considerar a ativacao operacional validada.
