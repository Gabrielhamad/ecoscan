# Ciclo das contribuicoes aprovadas

Aprovacao e revisao humana, nao treinamento. O banco mantem `queued` ate que
um processo rastreavel de treinamento e validacao incorpore o registro.

1. Na secretaria, exportar somente aprovadas. O pacote contem fotos privadas:
   nao publicar no GitHub nem compartilhar fora da equipe autorizada.
2. Importar em um diretorio novo, ignorado pelo Git:

```powershell
python scripts/import_approved_contributions.py ecoscan-aprovadas.zip data/reviewed_batches/lote_001
```

3. Revisar o manifesto e combinar com a base curada. Separar objetos/origens,
   evitando fotos semelhantes do mesmo objeto entre treino e teste. Um exemplo
   aprovado nao sustenta validacao independente de uma categoria.
4. Reprocessar os originais com o mesmo contrato usado na inferencia; nao anexar
   descritores antigos quando `model_processing_compatible` for falso.
5. Treinar candidato fora do Streamlit e comparar com o modelo anterior usando
   conjunto independente, precisao/recall por classe e taxa de rejeicao.
6. Publicar somente apos validacao, preservando modelo anterior e manifesto.

O importador valida consentimento, revisao, formato, tamanho, caminhos e conflitos
de rotulo entre arquivos identicos. Nao altera o modelo ativo ou marca a foto como
treinada. Nao confundir importacao com aprendizado concluido.

## Executor automatico

O workflow `training.yml` consulta as aprovacoes a cada seis horas ou por disparo
manual, sem exportacao pela secretaria. Nao executa em pull requests. Usa apenas
secrets do GitHub Actions e guarda modelos e metricas no bucket privado
`ecoscan-training`. Nenhuma imagem e publicada como artifact do GitHub.

Configuracao: secrets `ECOSCAN_SUPABASE_URL`, `ECOSCAN_SUPABASE_SERVICE_KEY`,
variavel `ECOSCAN_TRAINING_ENABLED=true`. A chave e privilegiada: acesso de escrita
ao repositorio deve ficar restrito aos mantenedores confiaveis.

O bucket precisa conter `corpus.json`, com `images` (lista de `key`, `class`,
`split`, `group`, `sha256`). Chaves comecam por `corpus/`; splits sao `train` e
`validation`; cada objeto/origem deve ter o mesmo grupo, sem cruzar os splits.
Exige pelo menos 20 imagens por classe em cada split. As correcoes aprovadas
entram apenas no treino. Configurar `bootstrap: true` apenas para permitir a
primeira publicacao sem referencia remota; depois a referencia ativa sempre e
comparada. O conjunto de validacao deve ser curado contra variacoes do mesmo
objeto das contribuicoes: hashes so detectam duplicatas exatas.

Estados: queued, waiting_dataset, training, validating, validation_failed,
published, failed. Sem corpus, registra waiting_dataset. Candidato so publica
com macro F1 >= 0.85, precisao e recall por classe >= 0.80 e ganho >= 0.01 sobre
a referencia sem queda de recall por classe. Esses limites sao criterios de
aceitacao, nao resultados medidos. O avaliador usa a saida do classificador;
a experiencia completa com regras de material/camera exige teste de campo.

O aplicativo consulta `active.json` a cada 60 segundos, valida hash, escopo,
contrato de preparo e revisoes, e carrega o artefato privado. Modelos anteriores
permanecem em `runs/` para rollback. Revisao revogada invalida a versao remota.
Nao executar dois workers fora do grupo de concorrencia do workflow.

## Verificacao operacional em 21/10/2026

GitHub Actions configurado e primeira execucao realizada:
https://github.com/Gabrielhamad/ecoscan/actions/runs/39611659743

O worker conectou ao Supabase e alterou o protocolo aprovado de `queued` para
`waiting_dataset`, com incremento de revisao de 2 para 3. Nao treinou nem publicou
modelo: o bucket privado ainda nao possui o corpus de treinamento e validacao.
O manifesto local `scope_corrected_v1` possui apenas 2 exemplos de pilhas e 1 de
eletronicos elegiveis para treino. Nao reutilizar as exclusoes para contornar isso.
# Preparacao verificavel do corpus privado

O comando abaixo prepara os arquivos para o executor sem enviar fotos ao GitHub
ou alterar o modelo em producao:

```powershell
python scripts/build_training_corpus.py --manifest data/curated/objects_v1_taco_reviewed/manifest.json --source data/curated/objects_v1_taco_reviewed --output reports/private_corpus_20261021
```

O diretorio de saida deve ser novo. A preparacao exige revisao por objeto,
confere SHA-256, rejeita duplicatas de arquivo e pixels decodificados, bloqueia
grupos de captura presentes em treino e validacao e preserva o conjunto de teste.
Ela nao realiza nova revisao visual nem identifica automaticamente fotos
parecidas do mesmo objeto. Essa verificacao continua necessaria na curadoria.

`corpus.json` descreve os arquivos privados; `readiness.json` informa contagens
e lacunas por classe. Um pacote pode ser preparado com `ready: false`: isso nao
autoriza publicar um modelo. O executor mantem suas verificacoes independentes.

Na execucao local de 21/10/2026, o lote TACO revisado forneceu 9 imagens de
plastico, 7 de papel/papelao e 7 de metal, todas destinadas a treino. Esse lote
nao contem validacao, vidro, pilhas ou eletronicos. Esses numeros descrevem
somente o lote exportado, nao todo o acervo historico. Nenhum novo modelo foi
treinado ou publicado com esse pacote. As fotos permanecem locais.

Validacao executada: 17 testes de corpus, executor automatico e modelo publicado
aprovados. Proxima dependencia: revisar e incorporar exemplos dos objetos
faltantes e uma validacao independente antes do envio ao armazenamento privado.

## Protecoes operacionais

Falhas de acesso ao armazenamento e JSON invalido encerram o lote como `failed`;
somente resposta explicita de objeto ausente permite `waiting_dataset`.
Os logs nao incluem os detalhes privados do erro do provedor. A publicacao
rejeita metricas ausentes, nao finitas ou fora do intervalo esperado, alem dos
limiares de qualidade. O modelo em uso nao e substituido por um candidato
reprovado. Downloads locais incompletos ou com checksum incorreto sao obtidos
novamente na proxima verificacao do cache, sem carregar o arquivo corrompido.

Testes automatizados exercitam publicacao e reprovacao com armazenamento e
treinamento simulados. Eles verificam a logica; nao representam medicao de
acuracia, treinamento real nem teste de conectividade da producao.
