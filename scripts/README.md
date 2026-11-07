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
| `prepare_delivery_pack.py` | Gera o pacote técnico para avaliação |
| `check_backup.py` | Valida um backup operacional sem restaurá-lo |

## Modelo e dados

| Comando | Finalidade |
| --- | --- |
| `run_inference.py` | Analisa uma imagem com a release ativa |
| `validate_semantic_onnx.py` | Confere integridade e inferência da release ONNX |
| `experiment_semantic_candidates.py` | Seleção offline auditada e teste final único; nunca publica modelo |
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
