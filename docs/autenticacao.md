# Acesso do cidadao e da secretaria

O parametro `?profile=admin_secretaria` nao concede permissao. O servidor
resolve a identidade em cada execucao a partir das informacoes verificadas pelo
login OIDC do Streamlit. Nao ha senha padrao ou administrador automatico.

## Configuracao

1. Cadastre um cliente Web no Google Auth Platform.
2. Cadastre a URI de retorno `http://localhost:8501/oauth2callback` para testes
   locais e `https://SEU-APP.streamlit.app/oauth2callback` para hospedagem.
3. Use `.streamlit/secrets.example.toml` como referencia para configurar
   `.streamlit/secrets.toml` localmente ou o painel Secrets da hospedagem.
4. Preencha client_id, client_secret e cookie_secret. Gere o cookie_secret com
   `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
5. Em `[access]`, mantenha o issuer do provedor e liste os e-mails dos gestores
   em `admin_emails = ["gestor@exemplo.com"]`.
6. Instale requirements.txt, reinicie e entre na conta pelo menu lateral.

O arquivo secrets.toml e ignorado pelo Git. Nunca publique credenciais reais.
O modelo secrets.example.toml nao ativa o login por si so.

## Regras

- Sem login configurado, somente o fluxo publico fica disponivel.
- Cada visitante recebe uma identidade aleatoria por sessao. Ao encerrar a
  sessao, pode perder acesso ao seu historico temporario.
- A conta autenticada tem identificador estavel derivado do emissor e subject,
  permitindo a mesma identificacao em dispositivos diferentes.
- A gestao exige e-mail verificado, emissor configurado e inclusao explicita
  na lista de administradores. E-mail nao listado continua como cidadao.
- Identidade expirada perde privilegios. A autorizacao e recalculada em cada
  execucao; a URL e o seletor antigo nao definem o papel.
- Registros antigos de usuario_demo e admin_secretaria nao sao transferidos
  automaticamente para uma conta real.

## Validacao antes de compartilhar

Teste um visitante abrindo o link administrativo, uma conta nao autorizada,
uma conta gestora, logout e remocao do e-mail da lista de autorizados.
Confirme que somente a conta autorizada recebe as abas administrativas.

Os testes automatizados cobrem a decisao de acesso e a interface sem provedor.
O redirecionamento e retorno reais dependem das credenciais do projeto.
Autenticacao nao substitui banco persistente, backups e protecao do servidor Live.

Referencia: https://docs.streamlit.io/develop/tutorials/authentication/google
