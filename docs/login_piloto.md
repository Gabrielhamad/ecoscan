# Login do piloto

Com persistencia Supabase configurada e OIDC ausente, o app oferece entrada por
email e senha usando Supabase Auth. Nao armazena senhas nem cria autenticacao propria.
O cliente de Auth e separado do cliente de banco e nao fica em cache compartilhado.

## Provisionamento

### Convite e confirmacao sao etapas distintas

O convite da equipe apenas informa o endereco do aplicativo e o procedimento de
cadastro. Usar `templates/analyst_invitation.txt` com envio individual, sem expor
a lista de destinatarios. Nao criar senhas compartilhadas nem usar convite
administrativo do Supabase neste fluxo: o app nao implementa callback de convite.

Ao enviar o formulario Criar conta, o Supabase envia a confirmacao automatica.
O template em portugues esta versionado em `templates/auth_confirm_signup.html`;
aplicar em Authentication > Emails > Confirm sign up com assunto
`EcoScan | Confirme seu cadastro`. Preservar `{{ .ConfirmationURL }}` e manter
Confirm email ativado. Alterar o arquivo no GitHub nao altera o template remoto.

Em 01/10/2026 foram conferidos Confirm email e SMTP personalizado ativos, e o
template em portugues foi salvo no Supabase. Em 03/10/2026, os tres convites
foram enviados pelo recurso de teste da equipe no Brevo; os logs registraram
entrega para cada destinatario. Isso nao comprova cadastro ou login concluido.

Nao ha email adicional de boas-vindas depois da confirmacao. Se necessario,
implementar esse evento no servidor com fila e deduplicacao, nunca em cada login
ou rerun do Streamlit. A mensagem automatica atual e a verificacao do cadastro.

### Cadastro breve preparado

O app possui abas Entrar/Criar conta. Cadastro solicita email, senha de 12 a 128
caracteres, confirmacao de senha e concordancia com tratamento do email para
autenticacao. Usa auth.sign_up, nunca criacao administrativa nem autoconfirmacao.
Nao concede sessao na resposta do cadastro: confirmar email e entrar normalmente.
Resposta de cadastro nao informa se a conta existe. Ha intervalo de 60 segundos
por sessao; os limites reais e protecao contra abuso dependem do Supabase.

Antes de ativar `public_signup_enabled = true` em `[access]`:

1. Configurar SMTP proprio no Supabase. O SMTP padrao so envia para emails da
   equipe do projeto e nao atende um cadastro publico dos colegas.
2. Manter Confirm email ativado; configurar Site URL para
   `https://ecoscan-gabrielhamad.streamlit.app` e conferir template de confirmacao.
3. Testar recebimento e confirmacao com um endereco externo autorizado pelo dono.
   O link confirma o email; o usuario volta ao app e entra com email/senha.
4. Verificar bloqueio de email nao confirmado, limites e erros; planejar CAPTCHA
   antes de divulgacao ampla. Nao habilitar CAPTCHA sem integrar o token no form.

Fonte: https://supabase.com/docs/guides/auth/auth-smtp

Visitantes consultam e analisam sem gravar historico, fotos de contribuicao,
relatos, testes ou pontos. A foto de analise ainda precisa ser processada pelo
servidor e pode usar arquivo temporario, removido ao final; logs tecnicos da
infraestrutura nao equivalem a perfil persistente. Dados antigos de visitantes
nao sao apagados nem vinculados automaticamente a novas contas.

1. Cada participante cria sua propria conta pelo formulario do aplicativo.
   Manter confirmacao de email; nao declarar emails confirmados sem verificar.
2. Configurar SITE_URL e redirecionamentos no Supabase antes de enviar convites.
   Para o piloto, preferir cadastro com confirmacao e entrada por senha. O callback
   implementado abaixo aceita apenas recuperacao; links de convite nao sao tratados
   como links de recuperacao.
3. No Streamlit Secrets, preservar [persistence] e adicionar:

```toml
[access]
supabase_admin_emails = ["EMAIL_VERIFICADO_DO_RESPONSAVEL"]
```

Lista vazia = nenhum administrador. OIDC continua com sua propria lista e issuer.
Papeis informados por URL, formularios ou user_metadata nao concedem permissao.
Nao usar a senha do banco como senha do usuario. Nunca versionar credenciais.

## Limites atuais

- No piloto publicado o cadastro foi ativado apos configuracao de SMTP e
  confirmacao. Em novos ambientes deve permanecer desativado ate essa validacao.
- Token fica somente na sessao Streamlit, sem cookie duravel e sem refresh nesta
  etapa. Se expirar ou falhar a verificacao, exige nova entrada e volta a visitante.
- get_user valida o token remotamente a cada execucao; falha nunca mantem admin.
- Sair limpa a sessao local. Token emitido continua sujeito ao prazo do provedor;
  revogacao global de dispositivos nao foi implementada no app.
- Login identifica protocolos e pontos entre dispositivos quando a persistencia
  operacional esta ativa; nao migra registros locais antigos.
- Relatos de visitante nao sao apropriados automaticamente por quem entrar depois.
- O fluxo de recuperacao esta implementado; entrega de email e aceite com contas
  reais dependem da configuracao abaixo. Nao enviar convites em massa.

## Conta de analista para o piloto 02

1. O responsavel cria sua propria conta pelo cadastro normal e confirma o email.
   Se o cadastro publico estiver desativado, concluir a preparacao de SMTP antes
   de habilita-lo. Nao criar conta compartilhada nem senha fixa no codigo.
2. Adicionar somente esse email confirmado a [access].supabase_admin_emails
   nos Secrets do servidor. O email e comparado sem diferenciar maiusculas.
3. Entrar com essa conta pela mesma aba Entrar. A interface identifica o analista
   e libera a Central de analise da secretaria. Selecionar um protocolo, conferir
   foto e rotulo, escrever a resposta e salvar a revisao.
4. O autor entra com a conta usada no envio e escolhe Perfil → Atualizar protocolos.
   O numero original e preservado. Outra conta nao recebe esse protocolo.
5. Para retirar acesso, remover o email da lista. Na proxima execucao a permissao
   e reavaliada e os dados privados da sessao anterior sao limpos.

Nao ha promocao pelo cadastro, parametros de URL ou metadados editaveis pelo
usuario. A verificacao usa get_user(token) a cada execucao. O cliente Auth e
separado do cliente de persistencia que usa a chave privada do servidor.

## Recuperacao de senha

No Supabase Authentication, configurar SMTP, Site URL para a URL HTTPS do app e
prazo de validade/limites de envio. Em Email Templates → Reset Password, usar:

    <a href="{{ .SiteURL }}/?token_hash={{ .TokenHash }}&amp;type=recovery">Definir nova senha no EcoScan</a>

Configurar Site URL sem barra final para esse template. O link deve apontar direto
para o app. Nao usar o template padrao com fragmento #access_token: o servidor
Streamlit nao recebe fragmentos do navegador. Nao usar esse template para convite
ou confirmacao de cadastro. Desativar rastreamento de links do provedor SMTP.

O usuario abre Entrar → Esqueci minha senha e solicita o email. A resposta nao
informa se a conta existe; ha intervalo de 60 segundos por sessao, complementado
pelos limites do Supabase. Ao abrir o link, o app remove os parametros da URL,
limpa qualquer conta anterior e mostra apenas o formulario de nova senha.
A validacao de uso unico (verify_otp, tipo recovery) ocorre somente ao salvar,
para nao consumir o link em uma previsualizacao automatica. Senha deve ter 12 a
128 caracteres e coincidir com a confirmacao. Links invalidos, expirados ou usados
nao alteram senha. Falhas apos consumir o link podem exigir uma nova solicitacao.

A troca usa update_user na sessao de recuperacao isolada, nunca a API administrativa
nem a sessao de outra conta. Ao concluir, exige novo login. Nao altera UUID da conta,
propriedade de protocolos ou permissoes de analista. Sessoes de recuperacao nao
sao promovidas a login do app. Tokens JWT ja emitidos em outros dispositivos
continuam sujeitos ao prazo de validade do provedor.

Referencias do contrato usado: [recuperacao](https://supabase.com/docs/reference/python/auth-resetpasswordforemail),
[validacao OTP](https://supabase.com/docs/reference/python/auth-verifyotp) e
[atualizacao do usuario](https://supabase.com/docs/reference/python/auth-updateuser).
