# Pacote de execução APS — Prompt 10

Referência oficial reconfirmada em 08/11/2026: `main` em
`89622ec714b815c216a9215ab9ba69999b39c6b8`. URL informada pelo grupo:
<https://ecoscan-gabrielhamad.streamlit.app>. Este trabalho não altera esse deploy,
o modelo publicado, banco, autenticação ou os PRs anteriores. Os PRs #20–#28
continuam desenvolvimento separado; sua existência não comprova integração.
O requisito informado do manual é programa computacional e apresentação;
Streamlit/Python 3.12 atende ao formato de execução. Não há solicitação de `.exe`.

## Problema e solução

O comando anterior exportava sete relatórios/inventários, sem o programa, lock ou
manifesto de integridade para execução. Sua API permanece disponível como
`legacy-report`; textos históricos desse inventário não aprovam entrega.

O modo `review` cria um ZIP executável de **um commit**, com perfil local explícito,
lock exato fornecido pelo operador, README curto e manifesto JSON. Não lê arquivos
do working tree como fonte do programa. Helpers/perfil/painéis gerados são overlays
identificados individualmente por hash; `source_sha` e `builder_sha` são distintos.
Um empacotador com alterações locais registra `builder_workspace_dirty=true` e
`builder_sha=null`; esse protótipo não equivale ao empacotador commitado.

`execution_package.py` trata snapshot, integridade e empacotamento; a API de
`delivery_pack.py` delega para ele. O launcher reaproveita o resolver ONNX e o
contrato existentes, sem inferência alternativa. `packaging` passa a ser dependência
direta do validador de locks; já estava instalada transitivamente. Não houve
atualização de bibliotecas nem inclusão de PyTorch.

## Gerar e verificar

Com Python 3.12 e dependências de desenvolvimento instaladas, usando pasta de
saída nova e ignorada pelo Git:

```bash
python scripts/prepare_delivery_pack.py review --ref SHA_COMPLETO --runtime-lock work/requirements.lock --ci-report work/ci.json --output reports/pacote-revisao
python scripts/prepare_delivery_pack.py verify reports/pacote-revisao/ecoscan-review-SHA12.zip
```

`SHA12` são os primeiros 12 caracteres do SHA completo. O parâmetro opcional
`--lock-ref SHA_DO_LOCK` confere os bytes de `requirements.lock` daquele commit.
Sem esse parâmetro, o lock continua identificado pelo SHA-256, com origem externa
explicitamente fornecida; sua revisão e teste permanecem necessários. O lock exige
versões exatas, hashes SHA-256, sem URLs/opções/comentários, atendimento às dependências do commit e ausência de
ferramentas de desenvolvimento ou bibliotecas pesadas de treino no pacote web.
O ZIP não inclui wheels. A instalação inicial requer Internet e wheels disponíveis
para o Python/sistema escolhido. Locks de outra plataforma exigem teste específico.

`ci.json` é uma observação sanitizada, conferida pelo operador na API do GitHub:

```json
{
  "source_sha": "89622ec714b815c216a9215ab9ba69999b39c6b8",
  "conclusion": "success",
  "run_url": "https://github.com/Gabrielhamad/ecoscan/actions/runs/42513163053",
  "kind": "github_api_observation",
  "release_acceptance": "not_approved"
}
```

Não colocar logs, credenciais, URLs assinadas ou aprovação nesse JSON. O script
valida esquema/SHA/URL, não autentica a observação remotamente. Sem arquivo, registra
`not_provided`. CI verde nunca muda `release_ready=false`: o comando produz somente
`review_candidate_not_release`, sem criação/publicação de tag ou release.

Saída: ZIP com raiz `ecoscan/`, cópia externa de `delivery_manifest.json` e
`SHA256SUMS`. O manifesto contém SHA completo, versão do Python, plataforma do lock,
todas as versões resolvidas, dependências críticas, hashes por arquivo, modelo,
cabeça, shards, encoder reunido, contrato, método de execução, CI, resultados
históricos e limitações. O ZIP não é assinado: comparar o checksum externo por
canal confiável. O verifier confere hashes/lista permitida sem extrair, recusa
duplicatas, links, caminhos inseguros, arquivos extras e conteúdo alterado.
Datas de geração/metadados ZIP podem mudar o checksum entre execuções; os hashes
de cada entrada permitem comparar o conteúdo efetivo do snapshot.

## Conteúdo e direitos

Entram apenas fontes `.py/.css/.html` de `src/ecoscan/`, entrada Streamlit,
metadados do projeto, documentação selecionada, configurações públicas enumeradas
no código e artefatos da versão `semantic-v1`. A licença MIT do encoder CLIP/OpenAI
acompanha os shards. A cabeça é parâmetro gerado pelo projeto. O empacotador não
concede nova licença ao código do grupo ou a arquivos de terceiros.

Não entram `.env`, `.streamlit/secrets.toml`, perfis/contas, datasets, seeds de
treino, fotos locais, logs, relatórios operacionais, backups ou raster original
de `assets/`. Configurações públicas incluem `education.json`, necessário no
import da UI. Links/fontes de conteúdo educativo e dados públicos permanecem
citados; não se copiam páginas ou imagens dessas fontes.

Os rasters originais não têm proveniência de licença comprovada para esta entrega.
O pacote gera painéis geométricos de cor usando `bin_color_hex`, nos caminhos
esperados pela UI. Isso mantém a página educativa, que exige um arquivo de imagem.
São elementos da interface, descritos em `ui_color_panels`/`origin`, nunca fotos,
dataset, resultado do classificador ou evidência PDI. Não se reutiliza o raster
original nem se lhe atribui licença nova.

O perfil local desliga histórico e modelos remotos, mantém `confirmation_required`
e contrato de processamento. O launcher remove variáveis `ECOSCAN_*` herdadas,
força Secrets vazios próprios, localhost por padrão e não inicia servidor Live ou
encerra processos alheios. Credenciais de hospedagem não são necessárias.

## Fotos autorizadas para cópia offline

Sem fotos reais fornecidas, o pacote contém somente `examples/README.md` e
`offline_real_photo_copy=manual_pending`. Não há substituição por imagem inventada.
O upload sintético do smoke é fixture técnica, fica fora da distribuição e não
produz métrica de campo.

Para adicionar fotos revisadas, usar `--photos-root RAIZ_LOCAL --photos-manifest
MANIFESTO_LOCAL.json`. Modelo vazio seguro:

```json
{"images": []}
```

Cada registro deve ter `path` relativo à raiz, `sha256` completo, `source_kind`
(`real_authorized_photo` ou `technical_fixture`), `license` (`CC0-1.0` ou
`CC-BY-4.0`), `attribution` autorizada, `distribution_allowed=true` e
`no_personal_data=true`. Essas declarações exigem revisão humana real dos direitos
e do conteúdo; não constituem consentimento por si sós. Outros termos precisam de
revisão antes de ampliar a lista. Remover metadados privados **antes** da aprovação
e recalcular hash; o script recusa EXIF extra/texto PNG e não reescreve a foto.
Recusa caminhos externos/links, duplicatas, arquivos inválidos, extensão divergente,
mais de 15 MiB ou 40 milhões de pixels. Copia bytes idênticos para nomes anônimos
`examples/photo_001.png` etc., preservando hash/licença/atribuição no manifesto.

Depois da cópia, o grupo precisa testar os exemplos offline no equipamento real;
a presença de fotos muda a pendência para `requires_device_smoke`, sem declarar
teste manual aprovado. Não inferir limpeza, conteúdo ou composição pela foto.

## Evidência executada em 08/11/2026

Snapshot do programa: `89622ec714b815c216a9215ab9ba69999b39c6b8`.
O lock usado no protótipo veio explicitamente do commit do PR #27
`5f255bfb934cf06466e04b21dba5bca2abe1544f`, com SHA-256
`83fc126c7aa632993e9b3107f28a108c80b88993764b71f24fb2157c8f22362e`.
Isso é entrada de empacotamento revisável, não melhoria já integrada à main ou
implantada. Reproduzir essa origem antes da integração:

```bash
mkdir -p work
git show 5f255bfb934cf06466e04b21dba5bca2abe1544f:requirements.lock > work/requirements.lock
```

Após integração, congelar novo SHA, usar o lock desse SHA e repetir os testes.
O smoke usou ambiente virtual novo, sem instalação editável do projeto,
Python **3.12.14**, Linux x86_64 e Chromium **156.0.8078.79**. Foram instalados
73 pacotes do lock com `uv 0.13.5 pip install --require-hashes --only-binary=:all:`;
o manifesto registra todas as versões. Uma primeira tentativa falhou por espaço
no temporário do ambiente Codex; a repetição em pasta própria terminou com sucesso.

| Item | Resultado real |
| --- | --- |
| Integridade do ZIP extraído | 180 arquivos listados verificados; protótipo de revisão |
| Primeira tentativa de abertura | Falhou por omissão de `education.json`; incluído e repetido |
| Abertura local como visitante | Passou, sem Secrets/contas/banco |
| Página Aprender | Passou com painéis de cor gerados |
| Upload técnico e análise ONNX CPU real | Passou; fixture sintética, sem acurácia de campo |
| Correção humana para Vidro | Passou; orientação Lixeira verde |
| Navegação e reabertura | Passaram; sem exceção visível ou erro JS no smoke |
| Navegador com requisições externas bloqueadas | Passou abertura/fluxo local; zero chamadas externas observadas |
| Inferência com conexões socket bloqueadas | Passou; contrato compatível e confirmação mantida |
| `run_delivery_demo.py verify` e `pip check` no venv novo | Passaram |
| Windows BAT/PowerShell, PC de apresentação, câmera/telefone físicos | `manual_pending` |
| Cópia offline de fotos reais autorizadas | `manual_pending` — nenhuma fornecida |
| Contas reais, Supabase e versão publicada | Não executados por este smoke |

Uma abertura demorou 1,815 s; uma inferência com carregamento demorou 1,336 s.
São observações únicas neste ambiente, sem benchmark de dispositivos ou promessa
de tempo. Evidência sanitizada: [smoke Linux](delivery/smoke_linux_2026-11-08.json).
O helper testado tem SHA-256
`9b47e27cf88f3a0d6f23e61e8528777c7c9b610bfd0fc5704ba4d65f413de036`.
O protótipo de smoke tinha empacotador ainda não commitado; seu manifesto não
falsifica `builder_sha`. O ZIP ignorado não foi publicado como release.

Verificações locais do PR: `python -m ruff check src scripts tests` passou;
`python -m pytest -q` passou com **516 testes e 108 subtestes**;
`python -m pip check` passou. A suíte específica
`python -m pytest tests/test_execution_package.py tests/test_delivery_pack.py -q`
passou com **19 testes**: snapshot commitado, exclusão de arquivos privados,
hash/licença/link inválidos, ZIP alterado/extra/inválido, lock sem pin ou com
opções/URLs/comentários, CI sem atalho de aprovação, isolamento de credenciais,
painéis de cor e cópia técnica autorizada sem reescrita. O resultado da CI do
head do PR deve ser conferido no próprio PR; estes números são da execução local.

A primeira CI deste PR, [run 42521848754](https://github.com/Gabrielhamad/ecoscan/actions/runs/42521848754),
falhou no teste existente de resolução remota (512 passaram e um falhou; PostgreSQL
passou). A falha foi reproduzida com relógio monótono em 0/5 s: cache vazio era
tratado como entrada `(None, 0)` válida por 60 s e nem consultava o store stub.
Com 100 s, o mesmo cenário passava. A correção pontual só reutiliza TTL quando a
chave já existe no cache; consentimento, hashes, validade e cache de falha continuam
iguais. Os cinco casos de `tests/test_published_model.py` cobrem relógios 0/5/100 s,
revogação e falha cacheada aos 0/30/61 s. A suíte combinada com empacotamento passou
com 24 testes; a suíte completa também passou com as flags da CI desabilitando
operações/comunidade. Esta correção de inicialização está no PR, sem alterar o
modelo remoto publicado. O ZIP do SHA oficial continua usando o código daquela
fonte e seu perfil local mantém modelos remotos desabilitados.

Versões críticas resolvidas, sem atualização por esta etapa: Streamlit 1.67.0,
ONNX Runtime 1.31.0, NumPy 2.5.4, Pillow 13.0.0, OpenCV headless 5.0.0.93,
scikit-learn 1.9.1 e Supabase 2.34.1. `semantic.json` mantém limiar 0,8.
O manifesto só reproduz métricas históricas compatíveis com os hashes, com
`independent_test=false`; não há ganho quantitativo novo ou promoção de modelo.

## Aceite e rollback

**Gate de release ainda bloqueado.** CI verde do SHA oficial não é aceite. O
diagnóstico do [PR #28](https://github.com/Gabrielhamad/ecoscan/pull/28) registra
P1 reproduzido localmente na main: mensagens de exceção podem alcançar UI/log;
correção está no PR #26 ainda não integrado. Falta smoke de apresentação e fotos
reais autorizadas. QA-09 e QA-18..QA-21 seguem `manual_pending`; nenhuma tag ou
release foi criada por este trabalho. O SHA implantado não foi verificado pelo
smoke local e melhorias de PR não são atribuídas ao site publicado.

Para liberar: integrar correções aceitas, registrar novo SHA candidato, confirmar
CI desse SHA, construir com empacotador commitado/lock revisado, conferir licença
e hashes, executar no PC real e registrar aceite explícito do grupo. Usar a matriz:

| Data UTC | SHA completo | Dispositivo/OS | Navegador/Python | Cenário | Status | Evidência sem PII |
| --- | --- | --- | --- | --- | --- | --- |
| preencher | preencher | PC da apresentação | preencher | instalação limpa, abrir e reabrir | `manual_pending` | preencher |
| preencher | preencher | PC da apresentação | preencher | foto real autorizada, confirmar/corrigir e destino | `manual_pending` | preencher |
| preencher | preencher | PC da apresentação | preencher | reabrir sem rede com exemplos revisados | `manual_pending` | preencher |
| preencher | preencher | PC/telefone autorizados | preencher | porta/rede local e câmera | `manual_pending` | preencher |

Somente depois desses gates, criar tag anotada apontando ao SHA aceito e publicar
ZIP/manifesto/checksum revisados. Não incluir credenciais, fotos privadas, logs
brutos, wheelhouse de terceiros sem termos ou evidência de contas reais.

Rollback: encerrar a instância, reabrir o pacote anterior por SHA e repetir
`verify`/smoke. Para reverter o código, reverter o commit deste PR por novo PR.
Não aplicar migrações, restaurar produção ou apagar Secrets/banco para voltar.
