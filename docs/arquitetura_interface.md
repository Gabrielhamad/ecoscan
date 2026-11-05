# Arquitetura modular da interface Streamlit

## Objetivo da refatoração

A interface principal do EcoScan acumulava aproximadamente 2.875 linhas no
arquivo `src/ecoscan/ui/streamlit_app.py`. A refatoração distribui a
apresentação por responsabilidade, sem alterar algoritmos de processamento,
release ONNX, regras de descarte ou esquema do Supabase.

A aplicação segue uma separação pragmática de camadas:

```text
streamlit_app.py                  # composição, navegação, sessão e políticas de acesso
  |
  +-- common_views.py            # textos, estados e tratamento de erros da apresentação
  +-- interaction_helpers.py     # arquivos temporários e assinatura da entrada
  +-- disposal_views.py          # cor de lixeira, pontos de entrega e impacto
  +-- processing_views.py        # etapas e evidências de processamento
  +-- campaign_views.py          # campanhas, missões e recompensas
  +-- civic_views.py             # relatos e acompanhamento
  +-- admin_views.py             # operações administrativas e testes de campo
  +-- system_views.py            # auditoria, diagnóstico e relatório
  |
  +-- services/                  # identidade, autorização, análise, persistência
  +-- app/ + image_processing/   # pipeline e operações de imagem
  +-- classification/            # inferência ONNX e contrato do modelo
  +-- disposal/                  # domínio e regras ambientais
  +-- config/                    # mapeamentos e opções explícitas
```

## Regras de dependência

1. O **coordenador** configura página, sessão, recursos, navegação e acesso e
   chama os componentes específicos. Ele não deve duplicar regras de domínio.
2. Os **componentes de apresentação** podem consultar serviços existentes,
   mas **não importam `ecoscan.ui.streamlit_app`**. Isso evita dependência
   circular e permite testar componentes isolados.
3. `common_views` e `interaction_helpers` não dependem das páginas.
   `campaign_views` e `civic_views` compartilham somente componentes menores
   de processamento e erros, não importam outra página inteira.
4. As validações de login e permissão devem continuar nos **serviços do
   servidor**, mesmo que botões de gestão não sejam exibidos ao visitante.
5. O modelo de classificação permanece assistido; apenas o usuário que
   confirmar uma categoria visual libera a orientação completa de descarte.
6. Métricas de reconhecimento não devem ser inseridas novamente no fluxo
   público. Testes e avaliações podem mantê-las internamente.

## Compatibilidade preservada

As funções `_render_*` existentes continuam acessíveis pelo módulo
`ecoscan.ui.streamlit_app` por meio de reexportações explícitas, preservando
importações de testes e de extensões internas. A função pública `main()` e
a entrada `streamlit_app.py` na raiz não mudam.

O projeto não foi migrado para um framework diferente nem introduziu
containers/serviços desnecessários para a APS.

## Como validar

```bash
python -m ruff check src scripts tests
python -m pytest -q
python -m pip check
```

A CI também aplica as migrations PostgreSQL e valida controle de acesso em
banco isolado. Os testes `tests/test_ui_modules.py` impedem dependências de
volta ao coordenador, ciclos entre componentes e crescimento descontrolado do
arquivo principal.

## Como acrescentar recursos

- Novo material ou descarte: editar as regras de `disposal/` e configurações
  ambientais, depois acrescentar somente a exibição em `disposal_views.py`.
- Novo filtro: implementar em `image_processing/`, integrar no pipeline,
  e acrescentar apenas o diagnóstico visual em `processing_views.py`.
- Nova missão: criar a regra no serviço de campanhas e a interface em
  `campaign_views.py`, sem replicar persistência no Streamlit.
- Novo painel administrativo: inserir em `admin_views.py`, manter a
  autorização no serviço e adicionar seu acesso no coordenador.
- Novos testes de campo: criar dados e serviços próprios e renderizar
  resultados em `admin_views.py`.

## Próximos limites de arquitetura

A função `main()` ainda coordena várias páginas dentro do mesmo fluxo de
execução. Uma próxima etapa pode extrair controladores por página e contratos
de sessão tipados, **desde que** sejam preservados os mesmos IDs de estado e
os percursos de visitante, usuário e gestor, com testes de integração.
