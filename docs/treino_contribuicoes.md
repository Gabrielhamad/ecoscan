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
