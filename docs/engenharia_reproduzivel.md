# Engenharia reproduzível e gates de qualidade

Base conferida em 08/11/2026: `89622ec714b815c216a9215ab9ba69999b39c6b8`.
O SHA final e a execução de CI constam no PR do Prompt 08. Não houve alteração
funcional do classificador, do modelo publicado, da autenticação ou das migrações.

## Instalar em clone novo

Ambiente validado: **Python 3.12.14, Linux x86_64**, mesmo alvo da CI e do Docker.
O lock fixa versões e hashes; não promete imagem binária idêntica entre sistemas,
plataformas ou atualizações do repositório Debian. Outros sistemas exigem teste.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes --only-binary=:all: -r requirements.lock -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
python scripts/check_dependency_lock.py --installed
python -m pip check
```

`requirements.in` e dependências de `pyproject.toml` são entradas declarativas
alinhadas; `requirements.lock` resolve **73 pacotes de runtime**. O lock de
ferramentas resolve **36 pacotes**, com sobreposição consistente ao runtime.
`requirements.txt` inclui o lock para que deploys que executam `pip install -r requirements.txt`
também usem a resolução fixa. `runtime.txt`, CI e Docker usam Python 3.12.14.
Instalação de desenvolvimento inclui build, teste e segurança; o Docker instala
somente runtime, sem pytest, Ruff ou ferramentas de auditoria.

Versões principais efetivamente resolvidas, preservadas do ambiente já testado:

| Pacote | Versão |
| --- | --- |
| ONNX Runtime | 1.31.0 |
| Streamlit | 1.67.0 |
| NumPy | 2.5.4 |
| OpenCV headless | 5.0.0.93 |
| Pillow | 13.0.0 |
| scikit-learn | 1.9.1 |
| scikit-image | 0.26.0 |
| Supabase | 2.34.1 |
| Authlib | 1.9.5 |
| pytest / Ruff | 9.2.0 / 0.17.4 |
| pip-audit / Gitleaks | 2.10.0 / 8.24.3 |
| setuptools / wheel (build) | 84.1.0 / 0.46.2 |

O runtime foi congelado sem upgrade em massa. A primeira auditoria do runtime
não encontrou vulnerabilidades conhecidas. Duas versões candidatas de build
(setuptools 80.9.0 e wheel 0.45.1) produziram quatro alertas; foram substituídas
pelas correções indicadas acima, antes de finalizar o lock. Não se configurou
ignore de CVE. A lista completa instalada é registrada pela CI sem URLs locais.

## Gates e reprodução

| Check do PR | O que reprova |
| --- | --- |
| `Testes e diagnostico local` | Ruff, pytest, pip check, divergência entre declarações/locks/instalado, importação de UI por camadas internas, ciclo de importação imediata, ONNX/hash/contrato incompatível ou inicialização com erro |
| `Migracao e permissoes PostgreSQL` | PostgreSQL 16; falha em qualquer migração na primeira ou segunda aplicação; violação de RLS/privilégios, CAS, evidência imutável e auditoria |
| `Segredos e dependencias` | Finding Gitleaks, scanner que não detecta canário, falha da ferramenta/API ou vulnerabilidade conhecida nos locks |
| `Container e inicializacao` | Falha de build, usuário diferente de 10001:10001 ou healthcheck Streamlit sem sucesso |

```bash
python -m ruff check src scripts tests
python -m pytest -q
python -m pip check
python scripts/check_architecture.py
python scripts/check_model_integrity.py
python scripts/check_startup.py
bash scripts/install_ci_gitleaks.sh /tmp/ecoscan-tools
python scripts/check_secrets.py --gitleaks /tmp/ecoscan-tools/gitleaks
python -m pip_audit -r requirements.lock -r requirements-dev.lock --require-hashes --disable-pip --cache-dir /tmp/ecoscan-audit
```

A inicialização verifica HTTP local real e renderização de visitante com AppTest;
não testa câmera física ou produção. O gate de modelo usa a implementação existente
em CPU e um RGB constante, valida partes, cabeça, classes e contrato, e monta o
encoder em diretório temporário. Isso não mede acurácia ou independência do dataset.
O gate de arquitetura verifica todos os módulos e importações proibidas inclusive
dentro de funções. Ciclos são avaliados nas importações imediatas; integrações
intencionalmente lazy, como `classification.runtime` → `published_model`, não são
prova de grafo runtime acíclico. Testes existentes de importação leve continuam ativos.

Para PostgreSQL, usar **banco descartável**, nunca produção:

```bash
psql -v ON_ERROR_STOP=1 -f tests/community_database_fixture.sql
for pass in 1 2; do
  for migration in migrations/*.sql; do
    psql -v ON_ERROR_STOP=1 -f "$migration"
  done
done
psql -v ON_ERROR_STOP=1 -c BEGIN -f tests/community_database_checks.sql
```

Esse comando depende de `PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE` de um
PostgreSQL 16 local isolado. A CI cria o serviço e usa somente registros sintéticos;
os testes terminam em ROLLBACK. Não foram alteradas migrations para obter verde.

```bash
docker build -t ecoscan-local .
docker run --rm --name ecoscan-local -p 127.0.0.1:8501:8501 ecoscan-local
```

O Docker fixa a versão de Python, instala o lock com hashes e roda como usuário
sem privilégios. Contexto exclui Secrets, `.env`, backups, logs, dados privados,
candidatos/remote models e caches de encoder. A CI apenas constrói/testa: não faz
push de imagem ou deploy. O treinamento existente recebe as mesmas dependências
fixadas e Actions por SHA; seus triggers/variável de ativação e gates de promoção
foram preservados, e nenhum treinamento de produção foi disparado por esta etapa.

## Atualizar uma dependência

1. Em branch própria, rever release notes e compatibilidade Python/ONNX. Alterar
   somente o pacote necessário nas declarações e seu lock, mantendo os outros pins.
2. Os locks foram gerados com **uv 0.13.5**, Python 3.12, `--generate-hashes`,
   `--no-emit-index-url`, `--no-annotate`, `--no-header`. Para recongelar sem upgrade:
   `uv pip compile requirements.in -c requirements.lock --python-version 3.12 --generate-hashes --no-annotate --no-header -o /tmp/runtime.lock`.
   Para atualizar, partir de uma cópia de constraints retirando apenas o pin alvo;
   não usar `--upgrade` global. Regerar ferramentas com `requirements-dev.in`
   e `-c requirements.lock` e revisar o diff de todas as versões.
3. Recriar venv e executar os quatro checks. Dependabot não sincroniza por si só
   todos estes arquivos de lock arbitrários; divergência reprova a CI.
4. Exigir nova CI no SHA atualizado; não aprovar pelo resultado de outro commit.

## Dependabot examinado individualmente

| PR / SHA consultado | Mudança | CI consultada e decisão |
| --- | --- | --- |
| [#1](https://github.com/Gabrielhamad/ecoscan/pull/1) / `564beaef1e2e36a47dacf4abcb91b32bb9addaef` | setup-python v6 → v7 | Run 41889912386: testes falharam, PostgreSQL passou; não integrar sem CI atual verde |
| [#2](https://github.com/Gabrielhamad/ecoscan/pull/2) / `87c9061e41d58988c406809fb88d2f5b107a5247` | checkout v6 → v7 | Run 41889927955: testes falharam, PostgreSQL passou; não integrar sem CI atual verde |
| [#3](https://github.com/Gabrielhamad/ecoscan/pull/3) / `84d863a4382ef393c9be5fd07dd7b75d4020dcca` | upload-artifact v6 → v7 | Run 41889944502: testes falharam, PostgreSQL passou; não integrar sem CI atual verde |
| [#4](https://github.com/Gabrielhamad/ecoscan/pull/4) / `bd5acaa88d28d9f0a41e8c8f3ed76753749e8127` | ONNX Runtime 1.31.0 → 1.31.1 | Run 41889961872: testes falharam, PostgreSQL passou; refazer contrato/probe e suíte com lock atualizado |

Os diffs e o passo com falha (`Testes automatizados`) foram consultados. Logs
detalhados não retornaram conteúdo nesta consulta; não se atribui a falha ao
upgrade sem reprodução. As Actions v6 foram mantidas e fixadas por SHA, sem
promover v7 ou trocar ONNX apenas por ser patch. Nenhum desses PRs foi integrado,
fechado ou aprovado automaticamente.

## Proteção de main: configuração ainda necessária

Consulta em 08/11/2026: endpoint da branch informou `protected=false`;
`GET /repos/Gabrielhamad/ecoscan/branches/main/protection` retornou **403 Resource
not accessible by integration**. Metadados da conta indicam admin, mas isso não
confere escopo à integração. Nenhum PUT de settings foi executado.

Após integrar os checks e obter execução verde, o mantenedor deve acessar
**Settings → Branches → Add branch protection rule**, padrão **main**, e marcar:

1. Require a pull request before merging; uma aprovação de pessoa real elegível,
   descartar aprovações antigas em novo push e exigir resolução das conversas.
2. Require status checks to pass; Require branches to be up to date. Selecionar
   exatamente os quatro checks da tabela acima, após aparecerem na CI.
3. Aplicar a administradores/bypass, bloquear force push e exclusão da branch.
4. Manter CODEOWNERS; habilitar revisão obrigatória por codeowner somente após
   cadastrar revisores reais suficientes (autor não pode aprovar o próprio PR).

Verificar novamente com `gh api repos/Gabrielhamad/ecoscan/branches/main/protection`
com credencial administrativa autorizada e conferir os contextos/strict/reviews.
O sucesso dos checks não comprova que essa configuração foi ativada.

## Artifacts, limites e rollback

Token de Actions tem apenas `contents: read`; checkout não preserva credenciais.
A varredura não usa `pull_request_target` ou Secrets de produção. Artifacts são
somente os cinco arquivos explicitamente listados no workflow: resumo de camadas,
hashes do modelo, startup e versões. Não inclui relatório de findings, fotos,
backups, banco, `.env`, logs de conta ou glob aberto de relatórios.

Gitleaks avalia texto rastreado atual, sem ler arquivos locais ignorados ou
seguir symlinks; não audita histórico Git nem conteúdo binário. O canário testa a
ferramenta, não prova ausência de todo segredo possível. pip-audit depende da base
externa de vulnerabilidades conhecidas e não é auditoria completa do sistema operacional.

Rollback: reverter este PR e reconstruir a imagem anterior. Não há migração de
produção nem troca de modelo. Reverter um pin com alerta reabre o risco reportado;
preferir corrigir a versão afetada quando possível. Não apagar banco ou dados para
restaurar o app. Retomar o lock anterior não dispensa CI e revisão do mantenedor.
