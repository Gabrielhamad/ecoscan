# Login do piloto

Com persistencia Supabase configurada e OIDC ausente, o app oferece entrada por
email e senha usando Supabase Auth. Nao armazena senhas nem cria autenticacao propria.
O cliente de Auth e separado do cliente de banco e nao fica em cache compartilhado.

## Provisionamento

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
   `https://ecoscan-gabrielhamad.streamlit.app/` e conferir template de confirmacao.
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

1. Criar/convidar cada participante em Supabase Authentication > Users.
   Manter confirmacao de email; nao declarar emails confirmados sem verificar.
2. Configurar SITE_URL e redirecionamentos no Supabase antes de enviar convites.
   O fluxo de convite/definicao de senha deve ser validado antes de convidar o grupo;
   esta versao do app ainda nao implementa callback de definicao/recuperacao de senha.
3. No Streamlit Secrets, preservar [persistence] e adicionar:

```toml
[access]
supabase_admin_emails = ["EMAIL_VERIFICADO_DO_RESPONSAVEL"]
```

Lista vazia = nenhum administrador. OIDC continua com sua propria lista e issuer.
Papeis informados por URL, formularios ou user_metadata nao concedem permissao.
Nao usar a senha do banco como senha do usuario. Nunca versionar credenciais.

## Limites atuais

- Cadastro publico fica desativado ate SMTP e confirmacao serem validados.
- Token fica somente na sessao Streamlit, sem cookie duravel e sem refresh nesta
  etapa. Se expirar ou falhar a verificacao, exige nova entrada e volta a visitante.
- get_user valida o token remotamente a cada execucao; falha nunca mantem admin.
- Sair limpa a sessao local. Token emitido continua sujeito ao prazo do provedor;
  revogacao global de dispositivos nao foi implementada no app.
- Login identifica protocolos e pontos entre dispositivos quando a persistencia
  operacional esta ativa; nao migra registros locais antigos.
- Relatos de visitante nao sao apropriados automaticamente por quem entrar depois.
- Necessario validar com contas reais, regras de email/SMTP do plano gratuito e
  fluxo de recuperacao antes de liberar cadastro geral. Nao enviar convites em massa.
