# Campanhas e relatos compartilhados

## Escopo desta entrega (M2)

O participante envia um relato de descarte com foto e local aproximado; a equipe
consulta a evidencia privada e responde; o autor acompanha o mesmo protocolo no
Perfil, inclusive em outra sessao. A secretaria publica a campanha ativa e edita
titulo, mensagem, objetivos, orientacoes e pontos educativos das missoes.

Nao foram acrescentados agendamento, notificacoes por e-mail nem novos tipos de
premios. A resposta fica no perfil. Um encaminhamento registrado no piloto nao
significa que a Prefeitura recebeu uma solicitacao oficial. Denuncias nao geram
pontos automaticos e nao entram no treinamento: correcao de reconhecimento tem
seu proprio fluxo de consentimento, revisao e promocao de modelo.

## Fluxo e responsabilidades

1. Visitante consulta orientacoes e analisa fotos, sem persistir relatos.
2. Conta com e-mail confirmado envia foto, local e descricao com consentimento.
3. O servidor revalida a sessao no Supabase Auth e obtem o autor; IDs ou papeis
   fornecidos pela tela nao concedem autorizacao.
4. A foto e orientada, reduzida a JPEG de ate 1 MB e gravada sem EXIF/GPS em bucket
   privado. Nenhuma URL publica e criada. A imagem para evidencia nao e um novo
   filtro de reconhecimento: a analise continua no pipeline existente.
5. O banco confirma o protocolo. Reenvio do mesmo formulario recupera esse
   protocolo; dados diferentes exigem iniciar outro relato.
6. Analista autorizado decide entre encaminhar, arquivar e solicitar nova foto,
   sempre com resposta. Original e historico nao sao sobrescritos.
7. Autor consulta status e resposta em Meus relatos; outra conta nao os recebe.

O identificador de reenvio permanece na sessao. Depois de encerrar a sessao,
confira o historico antes de reenviar: nao se promete deduplicacao de formularios
novos enviados de outro aparelho. A interface mostra os ultimos 100 protocolos.

## Arquitetura

- `services/community_store.py`: autorizacao, publicacao, idempotencia, consulta
  por autor, integridade da imagem e revisao condicional.
- `ui/community.py`: editor de campanha e protocolos do cidadao/secretaria.
- `migrations/003_community.sql`: campanha ativa, relatos e auditoria imutavel
  pela aplicacao, com revisao inteira e indices por autor/data.
- `ecoscan-civic-evidence`: bucket privado; download somente depois de validar
  autor ou analista e conferir o hash da foto.

RLS ativo e privilegios revogados para `anon`/`authenticated`. A chave
`service_role` fica apenas no servidor Streamlit; como ela contorna RLS, a
autorizacao explicita do servico e obrigatoria. Nao cachear clientes autenticados,
protocolos ou fotografias entre sessoes. Nao expor esta classe diretamente como
API sem repetir essa fronteira de autenticacao.

Campanha publicada e publica, mas o editor exige analista verificado. Sem primeira
publicacao no banco, a configuracao versionada aparece explicitamente como
campanha de referencia. Se uma consulta falha, nao se troca silenciosamente para
essa referencia. Publicacao concorrente exige recarregar e reconciliar o texto.
Mudancas nos pontos de uma missao valem para novas participacoes; transacoes
anteriores e identificadores das missoes sao preservados.

## Ativacao e retorno

1. Conferir diff e suite. Preservar banco, bucket e arquivos locais existentes.
2. Validar a migracao em transacao: substituir apenas o `commit` final da migracao
   pelo conteudo de `tests/community_database_checks.sql`, que termina em
   `rollback`. O teste de primeira publicacao exige ausencia de campanha; depois
   de a campanha existir, executar em banco isolado, nao remover a campanha real.
3. Aplicar `migrations/003_community.sql` integralmente. Ela nao importa CSVs nem
   altera tabelas anteriores. Conferir RLS, bucket privado e tabelas novas vazias.
4. Publicar codigo aprovado e adicionar `[community]` com `enabled = true`
   no Streamlit Secrets, sem reescrever credenciais existentes. Alternativa local:
   `ECOSCAN_COMMUNITY_ENABLED=true`. Nao colocar segredos no Git.
5. Entrar como analista, revisar a referencia e publicar. Outra conta deve ver
   a atualizacao ao recarregar; uma sessao aberta nao recebe notificacao push.
6. Executar aceite entre duas contas e um analista; conferir apos reinicio.

Para suspender o recebimento, usar `enabled = false` em `[community]`; os dados e
fotos permanecem no banco. A interface bloqueia novos relatos em vez de grava-los
localmente. Nao reverter para uma versao anterior a esta entrega que escreva CSVs
em producao. Nao desfazer a migracao apagando tabelas ou buckets.

Os CSVs antigos continuam intactos, mas nao sao misturados automaticamente com
protocolos autenticados. Uma importacao futura precisa validar identidade e
consentimento; nomes de demonstracao nao podem ser convertidos em contas reais.

## Limites e operacao

- Piloto limitado a 200 relatos e uma campanha ativa; 15 segundos entre novos
  relatos da mesma conta; ate 100 revisoes por protocolo.
- Falha remota informa indisponibilidade, sem sucesso ficticio ou historico vazio.
- Upload e transacao PostgreSQL nao sao atomicos. Um timeout pode deixar foto
  sem protocolo; o mesmo reenvio reutiliza a foto se o hash conferir. Nao apagar
  automaticamente evidencias apos timeout: a transacao pode ter sido confirmada.
- Antes de ampliar uso: reconciliar objetos orfaos, definir retencao e exclusao,
  monitorar quota/abuso e ensaiar backup de banco **e** Storage (M5).
- Consentimento nao dispensa orientacao para evitar rostos, placas e dados de
  terceiros. O retorno ocorre no perfil, sem pedir telefone adicional.

## Validacao

Em 05/10/2026: 314 testes Python aprovados (23 novos de servico/interface),
incluindo a suite com Streamlit 1.65 isolado. A CI tambem testa migracao e
reaplicacao em PostgreSQL 16 isolado; esse job nao usa segredos de producao.
O teste SQL passou no PostgreSQL do Supabase, inclusive executando gravacoes com
`service_role`, negando acesso direto a `authenticated`, verificando auditoria,
imutabilidade e atualizacao condicional. A transacao de testes foi desfeita.
Depois, a migracao foi aplicada ao projeto publicado: as tres tabelas novas
foram conferidas vazias e o bucket foi confirmado privado. Nenhum registro
de teste foi mantido e nenhuma tabela anterior foi alterada.

Essas evidencias nao substituem M3: cadastro/login reais, duas contas, envio com
consentimento, foto acessivel so aos autorizados, resposta visivel ao autor,
reinicio e reenvio. O aceite final depende desse percurso no app publicado.
