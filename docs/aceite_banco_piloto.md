# Aceite do Supabase e das contas

Estado revisado em 04/11/2026. O núcleo do aceite foi executado no projeto ligado
ao aplicativo publicado com duas contas controladas e um analista. A operação
completa ainda possui os itens pendentes descritos abaixo.

## Evidência integrada de 04/11/2026

No aplicativo público, com o código funcional `0ad6ed7`, o responsável confirmou:

- cadastro, confirmação de e-mail, entrada e saída de duas contas controladas;
- envio consentido de uma contribuição pela conta A e protocolo persistente;
- ausência do protocolo no perfil B e recuperação pelo perfil A após novo login;
- abertura da Central de análise por uma conta presente na allowlist;
- revisão com resposta salva, visível para A após recarregar e invisível para B.

A CI pública [run 48](https://github.com/Gabrielhamad/ecoscan/actions/runs/41894070190)
passou no mesmo hash, incluindo a suíte Python e o PostgreSQL 16 com as migrations
001–004. Não foram registrados e-mails, senhas, tokens, fotos ou protocolos.

Continuam pendentes no ambiente publicado: aplicar e validar a migration 004,
testar retirada do analista da allowlist, campanhas/relatos, pontos/testes de
campo, indisponibilidade controlada e restauração de backup.

## O que o código garante

- A chave `service_role` fica no servidor e nunca é enviada ao navegador.
- As tabelas usam RLS e revogam acesso direto de `anon` e `authenticated`.
- Fotos ficam em buckets privados, com JPEG de até 1 MB e remoção de EXIF.
- Cadastro, login e recuperação revalidam a conta no Supabase Auth.
- O papel de analista vem somente de `access.supabase_admin_emails`; metadados,
  query string e perfis locais não concedem acesso.
- Campanhas, relatos e a fila de correções validam o ator antes de usar a chave
  privilegiada. Um cidadão recebe somente os próprios protocolos.
- Revisões usam versão esperada; originais e histórico de relatos não podem ser
  sobrescritos silenciosamente.
- A CI aplica as quatro migrações em PostgreSQL 16, reaplica as migrações
  aditivas e testa RLS, privilégios, identidades, concorrência e auditoria.

## Preparação do projeto

1. Confirmar que o projeto é o mesmo configurado nos Secrets do Streamlit.
2. Executar, nesta ordem, `migrations/001_contributions.sql`,
   `002_operational_records.sql`, `003_community.sql` e
   `004_verified_identity_constraints.sql`.
3. Manter os buckets `ecoscan-contributions` e `ecoscan-civic-evidence` privados.
4. Configurar `persistence.url` e `persistence.service_key` apenas nos Secrets.
5. Manter `public_signup_enabled`, `operations_enabled` e `community.enabled`
   desativados até o recurso correspondente estar migrado e conferido.
6. Executar `python scripts/check_supabase_setup.py` em um ambiente seguro com
   as mesmas credenciais. O comando é somente leitura e oculta os valores.

A migração 004 usa constraints `NOT VALID`: elas bloqueiam imediatamente novos
IDs que não sejam de contas Supabase, sem falhar por dados antigos. Antes de
validá-las, consultar e tratar os legados:

```sql
select 'contributions' as origem, reporter_id as identidade
from public.ecoscan_contributions
where reporter_id !~ '^supabase_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
union all
select 'points', user_id from public.ecoscan_points
where user_id !~ '^supabase_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
union all
select 'field_tests', tester_id from public.ecoscan_field_tests
where tester_id !~ '^supabase_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
```

Com resultado vazio, validar as três constraints pelo SQL Editor. Não apagar ou
atribuir dados antigos a uma pessoa sem uma decisão documentada de migração.

```sql
alter table public.ecoscan_contributions
  validate constraint ecoscan_contributions_verified_reporter;
alter table public.ecoscan_points
  validate constraint ecoscan_points_verified_user;
alter table public.ecoscan_field_tests
  validate constraint ecoscan_field_tests_verified_tester;
```

## Matriz de aceite publicada

Use dois e-mails controlados, A e B, e um e-mail de analista. Não registre senha,
token, link de recuperação, e-mail completo ou foto nos relatórios.

| Teste | Resultado esperado |
| --- | --- |
| Cadastro A e B | Cada pessoa recebe confirmação e entra com sua senha |
| E-mail não confirmado | Entrada e recursos persistentes permanecem bloqueados |
| Contribuição de A | Protocolo persiste após recarregar e abrir outro dispositivo |
| Perfil de B | O protocolo, a resposta e a foto de A não aparecem |
| Usuário comum no endereço de gestão | Painel e fila não aparecem |
| Analista autorizado | Fila, foto privada e revisão ficam disponíveis |
| Remoção do analista da allowlist | Privilégio desaparece no próximo rerun |
| Resposta do analista | Aparece para A e permanece invisível para B |
| Relato cívico | Autor, isolamento, revisão e histórico sobrevivem ao reinício |
| Pontos e testes de campo | Persistem por conta e não duplicam a mesma evidência |
| Indisponibilidade simulada | O app informa falha e não cria histórico local divergente |

Depois do percurso, registrar data, hash do `main`, navegadores/dispositivos,
resultado por linha e apenas os oito primeiros caracteres dos protocolos. Repetir
o smoke de visitante, pois a evidência pública anterior corresponde a `e0cb494`.

## Critério de aprovação

O núcleo de contas, contribuição, revisão e isolamento está aprovado para piloto
controlado no hash acima. O banco completo fica aprovado quando a matriz estiver completa no mesmo hash
verde da CI, as constraints estiverem validadas, os dois buckets continuarem
privados e existir responsável por backup, retenção, exclusão e revisão. Até lá,
o estado é “núcleo validado, operação completa pendente”.
