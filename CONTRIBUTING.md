# Contribuindo com o EcoScan

Este guia organiza o trabalho do grupo. Não é necessário instalar o projeto para
testar: comece pelo [guia do participante](docs/guia_do_grupo.md).

## Antes de alterar

1. Consulte o [README](README.md), o escopo ativo e as limitações conhecidas.
2. Descreva a tarefa em uma issue: problema, resultado esperado e critério de aceite.
3. Combine o responsável para evitar alterações simultâneas conflitantes.
4. Crie uma branch curta por tarefa, por exemplo `docs/guia-testes` ou `fix/login-error`.

## Fluxo de desenvolvimento

```bash
git switch main
git pull --ff-only
git switch -c docs/guia-testes
```

Configure o ambiente conforme o README. Faça alterações pequenas e mantenha as
regras de negócio fora da interface sempre que possível. Mudanças em permissões,
persistência e classificação devem ter testes de regressão específicos.

```bash
python -m unittest discover -s tests
git diff --check
git status --short
```

Antes do commit, revise os arquivos individualmente. Não adicione datasets,
segredos, logs privados ou exportações de contas. Abra um pull request para revisão
de outro integrante; essa é a prática recomendada, não uma proteção de branch
já configurada pelo projeto.

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
