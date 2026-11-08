# Smoke da versão publicada: identidades, dispositivos e privacidade

Referência oficial confirmada pelo responsável em 08/11/2026:
`89622ec714b815c216a9215ab9ba69999b39c6b8` e
https://ecoscan-gabrielhamad.streamlit.app. Os PRs #20–#27 **não estão integrados**
e suas melhorias não foram atribuídas à versão publicada. Este PR instrumenta
o aceite; não publica código, modifica Secrets ou migra infraestrutura.

O [registro datado](deployment_smoke/2026-11-08/acceptance.md) contém os estados
por cenário e as versões/horários realmente observados. JSON e CSV no mesmo
diretório permitem revisão por máquina e planilha. Nenhum telefone, conta real,
foto ou protocolo foi fornecido/usado pelo Codex.

## O que foi e o que não foi verificado

- HTTP da URL respondeu 200 com cliente Python e cookies efêmeros para seguir
  redirecionamentos do host. Isso só verifica resposta inicial, não app/SHA/login.
- Chromium 156.0.8078.79, viewport 1280×900, tentou navegação anônima e encontrou
  `ERR_CERT_AUTHORITY_INVALID`. TLS permaneceu habilitado. É um bloqueio do
  cliente no ambiente Codex; não foi diagnosticado defeito no certificado do site.
- GitHub não retornou registros de deployment. Isso não significa ausência de
  deploy no Streamlit. O SHA completo publicado **não foi comprovado**.
- O código mostra apenas prefixo de 12 caracteres da revisão na UI. Prefixo,
  badge, main e CI não substituem SHA completo obtido do provedor/runtime.
- Configuração local do candidato: `semantic_onnx_assisted`,
  `models/semantic-v1/semantic.json`, formato `clip-probe-fp16-v1`, limiar **0,8**,
  `confirmation_required=true`. Os três shards e a cabeça foram verificados e o
  encoder foi montado pelo `resolve_encoder` existente em diretório temporário.
  Pesos/metadados ativos não foram escritos. Hashes completos constam no registro.
- `remote_models_enabled=true`: um modelo remoto pode sobrepor o artefato local.
  Portanto, esses hashes **não atestam o modelo carregado na URL pública**.
- **Achado P1 no código da main:** a fronteira `_render_user_error` repassa o
  detalhe bruto da exceção à UI/log. Uma fixture com marcador sintético, sem
  dados pessoais e com logger/UI substituídos por mocks, reproduziu a propagação.
  O caso `local_error_privacy` está **failed**. É uma falha técnica local do código
  candidato, não um incidente comprovado na URL pública. A correção proposta está
  no **PR #26, ainda não integrado/publicado**. Triar/integrar e repetir o teste
  antes de usar dados privados; este PR de auditoria não duplica aquela correção.
- PostgreSQL descartável local não chegou a iniciar: o driver Docker VFS esgotou
  espaço ao materializar a imagem. Foi removida somente a imagem de teste. As
  fixtures de RLS/permissões serão registradas como evidência técnica da CI do PR,
  separadas de qualquer aceite do Supabase publicado.

QA-09 e QA-18..QA-21 continuam `manual_pending` neste instrumento. Não se alterou
`acceptance_checks.py`: seus gates externos continuam pendentes. Mesmo todas as
linhas de smoke passadas exigem revisão formal separada; `check` retorna 2.
Um retorno 0 de `init`, `probe` ou `record` significa que o registro foi salvo.

## Preparar e atualizar o registro

Com o ambiente do projeto e Python 3.12, em clone do candidato:

```bash
python scripts/audit_published_deployment.py init \
  --candidate-sha 89622ec714b815c216a9215ab9ba69999b39c6b8 \
  --url https://ecoscan-gabrielhamad.streamlit.app \
  --output reports/aceite_publicado
python scripts/audit_published_deployment.py probe \
  --report reports/aceite_publicado/acceptance.json
python scripts/audit_published_deployment.py check \
  --report reports/aceite_publicado/acceptance.json
```

`init` compara configuração e JSON do modelo ao commit informado, verifica a
cabeça/shards e prepara 31 cenários. Não faz login ou consulta o Supabase. O
fingerprint é do checkout local, separado do modelo efetivamente publicado.
`probe` só navega anonimamente. Não envia foto, contribuição ou formulário.
O browser opcional requer Playwright em ambiente de testes separado, sem alterar
as dependências web; por exemplo instalar `playwright==1.64.1` e seu Chromium.
Usar `probe --browser`; no Codex foi usado também
`--chromium /usr/bin/chromium --container-browser` por compatibilidade do container.
Esse último parâmetro não altera TLS nem o aplicativo. Não usar bypass de TLS.

Antes de marcar uma linha passada, o grupo deve executar o cenário de fato,
obter o SHA completo servido, anotar família/versão real do navegador, data com
fuso e um alias de evidência anonimizada. Exemplo **com placeholders**, não um
resultado já obtido:

```bash
python scripts/audit_published_deployment.py record \
  --report reports/aceite_publicado/acceptance.json \
  --case pc_visitor --status passed \
  --observed-sha SHA_COMPLETO_OBSERVADO \
  --at DATA_REAL_ISO8601_COM_FUSO \
  --browser Chrome --browser-version VERSAO_NUMERICA_REAL \
  --evidence EVID-010
```

Para A/B/analista, acrescentar `--authorization-confirmed` **somente após obter
permissão explícita para contas controladas**. A flag registra uma declaração do
operador, não concede acesso. Nunca colocar senha, token, e-mail, protocolo,
link assinado, caminho de foto ou observação privada na linha de comando/JSON.
O schema recusa campos extras e usa aliases EVID-001, mantendo o original
anonimizado em repositório de evidências do grupo, fora do Git público.

`published_model` exige `--runtime-fingerprint arquivo.json`, com exatamente
`metadata_sha256`, `head_sha256`, `encoder_sha256`, `processing_sha256` medidos
no runtime publicado. O arquivo não pode ter credenciais ou conteúdo de imagens.
Os quatro hashes precisam coincidir com o candidato congelado. Se o override
remoto for o esperado, primeiro formalizar a versão candidata correta; não
editar o relatório para esconder divergência.

Para uma linha não executada, usar `--status manual_pending --reason no_device`
ou os motivos oferecidos por `record --help`. A atualização gera os três formatos.
Não reutilizar resultados de outro SHA; após integrar PRs, congelar novo candidato,
reexecutar CI, gerar novo relatório e repetir os cenários atingidos.

## Percurso publicado em PC, Android e iPhone

Executar cada grupo no navegador real informado, sem converter emulação em prova
sobre telefone físico. Se não houver dispositivo/conta autorizada/foto, manter
`manual_pending`. Não remover controles do app para obter um resultado positivo.

1. **Versão:** no painel do Streamlit autorizado, conferir repositório, branch,
   entrypoint e SHA completo da implantação. Cruzar com revisão do runtime; a
   legenda de 12 caracteres é só indicação. Registrar apenas SHA e EVID-xxx.
2. **Visitante:** janela anônima nova, sem login. Confirmar ausência de gestão e
   de dados/protocolos alheios; navegar entre Escanear, Descarte, Mapa e Perfil.
3. **Captura:** foto real autorizada, um objeto principal; testar câmera permitida
   e negada com alternativa de upload. Testar JPG com EXIF, PNG, inválido e foto
   enorme. Conferir orientação, mensagem de erro e possibilidade de continuar.
4. **Análise:** registrar hipótese/rejeição/modelo indisponível sem porcentagem
   inventada. Explicar processamento. O tempo só deve aparecer se foi medido.
   Esse smoke não mede acurácia independente; QA-09 precisa do protocolo de campo.
5. **Confirmação/descarte:** escolher conscientemente outra classe e conferir
   destino correspondente; pilhas/eletrônicos exigem coleta especial. Não
   confundir hipótese automática com confirmação humana ou composição química.
6. **A/B autorizadas:** dois perfis de navegador separados. A envia evidência
   consentida; B não encontra registro, imagem ou resposta de A. Voltar a A,
   atualizar, sair/entrar e confirmar persistência. Guardar só EVID-xxx no relatório.
7. **Analista autorizado:** validar gestão pela allowlist; usuário B e visitante
   não devem obter privilégio por query string/perfil. Revisar a evidência de A
   somente com autorização; A vê a resposta após reabrir, B permanece isolada.
8. **Reabertura:** fechar navegador, reabrir e validar login/persistência. Nova
   captura não pode reutilizar uma confirmação inadequada da imagem anterior.
9. **Erro do banco:** somente em cópia isolada autorizada, simular timeout/falha;
   exigir mensagem sem PII e sem recibo de sucesso ou retry de gravação incerta.
   Em produção, observar apenas incidentes já ocorridos com autorização, sem induzir falha.
10. **Recuperação:** ensaiar restore/retorno somente em ambiente descartável
    separado, nunca sobre produção. Manter QA-21 pendente até evidência revisada,
    responsáveis e política de retenção/exclusão definidos.

As contas A/B e o analista são aliases de teste; não são identidades criadas pelo
Codex. Não experimentar IDs de contas reais ou forçar acesso a registros alheios.
Se aparecer dado de terceiro a visitante, interromper o teste e comunicar por
canal privado, sem publicar o conteúdo da tela.

## RLS/permissões e rollback

A CI usa PostgreSQL 16 isolado, `tests/community_database_fixture.sql`, migrations
001–004 e `tests/community_database_checks.sql`; verifica RLS, privilégios diretos
negados a anon/authenticated, identidades, concorrência e auditoria. O teste usa
registros sintéticos e termina com ROLLBACK. Não aponta para Secrets/URLs de
produção, não testa buckets do projeto publicado e não aprova QA-18/QA-19.
A prova de identidade de A/B depende também da camada servidor e do deployment.

Rollback deste PR: reverter apenas o código de relatório/CLI e a documentação.
Não há mudança de autenticação, migração, Secrets, modelo publicado ou deploy.
Os registros gerados são locais; não apagar evidência privada ou banco ao reverter.
