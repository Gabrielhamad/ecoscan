# Arquitetura modular da interface Streamlit

## Objetivo da refatoração

A interface principal do EcoScan acumulava aproximadamente 2.875 linhas no
arquivo `src/ecoscan/ui/streamlit_app.py`. A refatoração distribui a
apresentação por responsabilidade, sem alterar algoritmos de processamento,
release ONNX, regras de descarte ou esquema do Supabase.

A aplicação segue uma separação pragmática de camadas:

```text
streamlit_app.py                  # composição das páginas (~100 linhas em main)
  |
  +-- navigation_controller.py  # abas por papel, ativação sob demanda
  +-- session_state.py          # estado tipado de análise e ingestão
  +-- processing_configuration.py # controles e opções técnicas
  +-- analysis_controller.py    # foto, inferência e descarte confirmado
  +-- analysis_widgets.py       # captura, dicas e feedback
  +-- technical_page_controllers.py # base, processamento e sistema
  |
  +-- common_views.py           # textos, estados e erros
  +-- interaction_helpers.py    # arquivos temporários/assinaturas
  +-- disposal_views.py         # orientação de descarte
  +-- processing_views.py       # etapas e evidências de imagem
  +-- campaign_views.py         # campanhas e missões
  +-- civic_views.py            # relatos e protocolos
  +-- admin_views.py            # gestão administrativa
  +-- system_views.py           # indicadores e auditorias
  |
  +-- services/                 # autorização, persistência e casos de uso
  +-- app/ + image_processing/  # pipeline de imagens
  +-- classification/           # modelo semântico ONNX
  +-- disposal/                 # regras ambientais e destinos
```

## Regras de dependência

1. O **coordenador** apenas inicializa recursos e identidade, escolhe os
   controladores de página por perfil e cria a navegação. A sessão de análise,
   os parâmetros de processamento e as interações com fotos são delegados a
   contratos próprios, sem duplicar regras de domínio.
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

## Estado após a segunda refatoração

Os controladores de navegação e de página foram extraídos sem alterar a entrada
do Streamlit ou os nomes das abas. Os campos de análise têm acesso tipado por
`AnalysisSession`, que preserva as chaves existentes:
`last_analysis_result`, `last_analysis_signature`,
`last_analysis_source`, `last_history_saved_signature` e
`dataset_ingestion_results`. O estado de login permanece sob responsabilidade
da camada de identidade; invalidar uma foto não apaga credenciais ou rascunhos.

O controlador de navegação mantém `main_navigation_user` e
`main_navigation_admin`. A aba da câmera permanece montada enquanto o
usuário alterna abas. Campanhas, área administrativa e demais páginas pesadas
são executadas apenas quando ativadas. Os testes de regressão protegem
exatamente esses contratos.

Os fluxos de domínio existentes (ONNX, preparação RGB, banco, permissões,
cores de lixeira e confirmação humana) continuam fora do coordenador.
O serviço de câmera ao vivo segue separado do Streamlit Cloud.

## Próximas oportunidades

- Avaliar se o estado de ingestão e o histórico técnico precisam de repositórios
  específicos quando houver múltiplas instâncias do servidor.
- Repetir o aceite manual no aplicativo publicado, em Android e iPhone, após
  a mudança de organização da interface.
- Evitar novas abstrações antes de existir um caso de uso concreto, mantendo
  os módulos atuais testáveis, coesos e com dependências acíclicas.
