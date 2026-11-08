# Contribuindo com o EcoScan

Este guia organiza o trabalho do grupo. Não é necessário instalar o projeto para
testar: comece pelo [guia do participante](docs/guia_do_grupo.md).

## Antes de alterar

1. Consulte o [README](README.md), o [plano de gestão do projeto](docs/gestao_projeto.md), o escopo ativo e as limitações conhecidas.
2. Descreva a tarefa em uma issue: problema, resultado esperado, critério de aceite, evidência, prioridade e dependências (veja o [roadmap](docs/roadmap_entrega.md)).
3. Combine o responsável para evitar alterações simultâneas conflitantes.
4. Crie uma branch curta por tarefa, por exemplo `docs/guia-testes` ou `fix/login-error`.

## Fluxo de desenvolvimento

```bash
git switch main
git pull --ff-only
git switch -c docs/guia-testes
```

Configure o ambiente pelos locks conforme o README; evite atualizar dependências fora do objetivo do PR. Faça alterações pequenas e mantenha as
regras de negócio fora da interface sempre que possível. Mudanças em permissões,
persistência e classificação devem ter testes de regressão específicos.

```bash
python -m ruff check src scripts tests
python -m pytest -q
python -m pip check
python scripts/check_dependency_lock.py --installed
python scripts/check_architecture.py
python scripts/check_model_integrity.py
python scripts/check_startup.py
python scripts/run_acceptance_checks.py --diagnostic
git diff --check
git status --short
```

Antes do commit, revise os arquivos individualmente. Não adicione datasets,
segredos, logs privados ou exportações de contas. Abra um pull request para revisão
de outro integrante; essa é a prática recomendada, não uma proteção de branch
já configurada pelo projeto.

O workflow de qualidade executa testes e diagnóstico sem segredos de produção.
Antes da entrega final, execute o mesmo comando sem `--diagnostic`: pendências
retornam 2 e falhas retornam 1. CI verde não substitui o aceite real; consulte
[roadmap de entrega](docs/roadmap_entrega.md) antes de declarar um marco concluído.

## Checklist de revisão

- Problema e solução descritos, sem refatorações fora do escopo.
- Testes executados e resultado registrado; limitações de teste explícitas.
- Fluxos de visitante, participante e analista preservados.
- Nenhuma credencial ou informação pessoal no diff e nas capturas.
- Comportamento de erro verificado, sem mascarar falhas do banco.
- Documentação atualizada e, quando necessário, plano de migração/retorno.
- Para interface: teste de toque, texto legível, erros e estados vazios em celular e PC.
- Para reconhecimento: comparação com conjunto independente, não apenas exemplos de treino.

## Reportar problemas

Erros de reconhecimento com foto devem usar o fluxo consentido do aplicativo.
Para bugs de software, registre em issue: navegador, dispositivo, passos,
comportamento esperado, observado e mensagem de erro sem dados privados.
Não coloque senha, token, e-mail de terceiros ou protocolo identificável em issue.

Uma suspeita de acesso indevido deve ser comunicada diretamente ao mantenedor do
grupo, sem explorar contas alheias ou publicar detalhes antes da correção.

## Dataset e modelo

Use apenas imagens próprias consentidas ou fontes com direitos compatíveis.
Registre origem, licença, categoria, estado do objeto e identificação da cena.
Fotos do mesmo objeto e quadros do mesmo vídeo não podem atravessar os conjuntos
de treino e avaliação. Não use aumentos artificiais como evidência de diversidade real.

Revisão humana, treino e publicação são decisões separadas. Guarde a versão e o
hash do modelo, resultados por classe e casos de regressão. Uma aprovação na fila
não autoriza substituir o artefato ativo. Não exclua dados antigos sem inventário,
backup e decisão explícita do responsável.

## Publicação

O mantenedor revisa e integra a mudança. Após a implantação, confira a versão
servida e os fluxos afetados. Se houver regressão, preserve os dados e reverta o
commit responsável de maneira revisada; não apague o banco para restaurar o app.

## Dependências, CI e proteção de branch

Os locks de runtime e ferramentas têm versões/hashes exatos. `requirements.in` e
`pyproject.toml` continuam sendo entradas declarativas; o deploy usa
`requirements.lock`. Uma atualização precisa ajustar o lock e executar todos os
gates; não integrar PR do Dependabot apenas por ser patch/automático. Revisar
cada PR e seu SHA/CI individualmente. Não usar `continue-on-error`, ignorar CVEs
ou afrouxar o contrato do modelo para obter verde.

Os quatro checks requeridos e os passos de configuração de `main` estão no
[guia reproduzível](docs/engenharia_reproduzivel.md). A consulta pública informou
`protected=false`, e a API detalhada respondeu 403 para a integração. Este PR
não ativa proteção nem altera settings do repositório.

Artifacts de qualidade contêm somente os resumos e versões explicitamente
listados no workflow; não ampliar o glob para fotos, logs, backups, diretórios de
contas, `.env` ou Secrets. Não incluir findings de segredo em artifacts.
