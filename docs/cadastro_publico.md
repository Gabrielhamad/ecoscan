# Cadastro publico

O cidadao cria a propria conta, sem convite ou aprovacao da secretaria. O cadastro
solicita nome, e-mail, senha e consentimento. O nome fica no Supabase Auth como
`user_metadata.display_name`; nunca determina permissoes.

## Jornada

1. Visitante pode usar os recursos publicos sem cadastro.
2. Em Criar conta, preenche os dados e confirma seu e-mail uma unica vez.
3. Volta para Entrar e utiliza e-mail e senha. Nao precisa de convite.
4. Reportes e participacao continuam vinculados ao UUID autenticado existente.
5. Recuperacao de senha e um fluxo separado para contas existentes, inclusive
   contas anteriormente convidadas que ainda nao definiram uma senha.

Nao criar outra conta para resolver recuperacao. Nao confirmar e-mails manualmente
nem conceder papel de analista por metadados fornecidos no cadastro.

## Configuracao e operacao

- Manter `access.public_signup_enabled = true` no aplicativo e cadastro habilitado
  no Supabase; manter a verificacao de e-mail.
- Configurar o template Reset password conforme `login_piloto.md`. Usar
  `SiteURL` com a URL raiz publicada e `?token_hash=...&type=recovery`.
  O link padrao ConfirmationURL nao abre o formulario de recuperacao do Streamlit.
- A aplicacao consome o token somente ao salvar a senha, nao ao abrir o link.
- Mensagens de cadastro e recuperacao nao revelam se um e-mail tem conta.
- Analistas continuam definidos pela lista autorizada no servidor.

## Validacao

Testes automatizados cobrem cadastro publico, metadados sem privilegios,
consentimento, validacao, recuperacao e separacao de contas. A entrega do e-mail
e o login com a senha escolhida precisam tambem de teste manual pelo titular.
Nao registrar senhas, tokens ou links pessoais nos relatorios de teste.
