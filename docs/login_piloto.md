# Login do piloto

Com persistencia Supabase configurada e OIDC ausente, o app oferece entrada por
email e senha usando Supabase Auth. Nao armazena senhas nem cria autenticacao propria.
O cliente de Auth e separado do cliente de banco e nao fica em cache compartilhado.

## Provisionamento

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

- Contas devem ser provisionadas pelo responsavel; cadastro publico nao ativado.
- Token fica somente na sessao Streamlit, sem cookie duravel e sem refresh nesta
  etapa. Se expirar ou falhar a verificacao, exige nova entrada e volta a visitante.
- get_user valida o token remotamente a cada execucao; falha nunca mantem admin.
- Sair limpa a sessao local. Token emitido continua sujeito ao prazo do provedor;
  revogacao global de dispositivos nao foi implementada no app.
- Login identifica protocolos entre dispositivos, nao migra campanhas/pontos.
- Relatos de visitante nao sao apropriados automaticamente por quem entrar depois.
- Necessario validar com contas reais, regras de email/SMTP do plano gratuito e
  fluxo de recuperacao antes de liberar cadastro geral. Nao enviar convites em massa.
