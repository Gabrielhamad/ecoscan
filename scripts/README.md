# Ferramentas de engenharia

Os scripts desta pasta são comandos operacionais do produto atual. Execute-os a
partir da raiz do repositório, com o ambiente virtual ativo. Eles não fazem parte
da inicialização pública do Streamlit.

## Validação e entrega

| Comando | Finalidade |
| --- | --- |
| `run_acceptance_checks.py` | Executa os gates locais e gera evidências |
| `check_deployment_ready.py` | Verifica configuração e prontidão do deploy |
| `check_supabase_setup.py` | Confere tabelas e buckets privados sem alterar dados |
| `benchmark_startup.py` | Mede importação e primeira renderização do app |
| `diagnose_project.py` | Inspeciona dependências, modelo e diretórios |
| `prepare_delivery_pack.py review --ref SHA --runtime-lock LOCK --output reports/PASTA_NOVA` | ZIP executável para revisão; exige snapshot e lock exato com hashes |
| `prepare_delivery_pack.py verify ARQUIVO.zip` | Confere a lista permitida e hashes sem extrair o ZIP |
| `prepare_delivery_pack.py legacy-report` | Inventário antigo; não é distribuição executável nem aprovação |
| `run_delivery_demo.py verify` / `serve` | Verifica versões/modelo e inicia Streamlit local, sem credenciais herdadas |
| `check_backup.py` | Valida um backup operacional sem restaurá-lo |

## Modelo e dados

| Comando | Finalidade |
| --- | --- |
| `run_inference.py` | Analisa uma imagem com a release ativa |
| `validate_semantic_onnx.py` | Confere integridade e inferência da release ONNX |
| `evaluate_bundled_model.py` | Reproduz a avaliação histórica da release sem chamá-la de teste independente |
| `run_reviewed_training.py` | Processa a fila privada de contribuições aprovadas |
| `build_training_corpus.py` | Monta um corpus a partir de fontes revisadas |
| `build_semantic_learning_seed.py` | Gera a semente versionada do aprendizado revisado |
| `dataset_readiness.py` | Mede cobertura e qualidade do conjunto de dados |
| `evaluate_object_annotations.py` | Exporta anotações COCO revisadas |

Os comandos `capture_*`, `ingest_*`, `prepare_*`, `review_*` e `apply_*` apoiam
captura e curadoria auditável. Nenhuma captura é promovida automaticamente ao
modelo ativo. Os demais comandos geram evidências de processamento ou executam
demonstrações locais documentadas em `docs/`.

Arquivos em `reports/`, `data/` e segredos locais não devem entrar no Git. Uma
nova release exige proveniência, conjunto independente, métricas por classe,
hashes e possibilidade de retorno à versão anterior.

O procedimento de pacote, limitações de plataforma e aceite do SHA está em
[Pacote de execução APS](../docs/pacote_execucao_aps.md). Os launchers de apresentação
usam `run_delivery_demo.py`; os demais scripts continuam fora do fluxo público.
