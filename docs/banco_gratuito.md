# Banco gratuito: ativacao e limites

## Estado real

Integracao opcional preparada para Supabase Free: protocolos de reconhecimento,
rotulo/estado informado, consentimento, revisao/resposta e fotos privadas.
Sem credenciais, permanece o modo local temporario. Se configurado e indisponivel,
o sistema falha explicitamente: nao troca silenciosamente para arquivos locais.

Pontos de missao e registros de testes possuem adaptador remoto com ativacao
separada, apos a migration 002. Arquivos CSV antigos nao sao importados automaticamente.
Nao migrados: campanhas, denuncias e artefatos de modelos. Login Supabase foi
implementado, mas provisionamento das contas e autorizacao de analistas exigem
configuracao e aceite (ver login_piloto.md).
Treino na hospedagem fica desativado quando o banco esta ativo: exportar aprovadas
e treinar localmente ate implementar persistencia dos candidatos.

## Ativacao pelo responsavel

1. Criar conta em https://supabase.com/dashboard e um projeto numa organizacao Free.
   Nao contratar Pro nem habilitar recursos pagos para este piloto.
2. No SQL Editor do projeto, executar migrations/001_contributions.sql.
3. Conferir tabela ecoscan_contributions com RLS ativo e bucket
   ecoscan-contributions PRIVADO. Nao criar politicas de leitura publica.
4. Configurar apenas em Streamlit Cloud > App settings > Secrets:

```toml
[persistence]
url = "https://SEU_PROJETO.supabase.co"
service_key = "CHAVE_SERVICE_ROLE_DO_SERVIDOR"
```

Nao enviar a chave no chat, no GitHub, em screenshots ou no navegador do cidadao.
O backend usa chave privilegiada; analistas precisam de identidade verificada
e email explicitamente autorizado. Nunca tornar admin um visitante por parametro da URL.

5. Reiniciar app e enviar foto de teste sem pessoas ou dados pessoais.
6. Conferir registro na tabela e foto no bucket. Reiniciar novamente e conferir
   que a secretaria ainda ve a contribuicao. Confirmar anon/authenticated sem
   acesso direto ao banco/bucket e que um cidadao nao ve protocolos de outro.
7. Configurar login e autorizar emails dos analistas conforme autenticacao.md.

Os passos de SQL e acesso real ainda exigem validacao no projeto provisionado.
Testes locais com doubles verificam a integracao, nao substituem esse aceite.

## Pontos e testes: implantacao em duas fases

1. Publicar o codigo com `operations_enabled` ausente ou `false`.
2. Executar `migrations/002_operational_records.sql` no SQL Editor.
3. Verificar RLS nas duas tabelas, ausencia de leitura para anon/authenticated
   e permissoes select/insert somente para service_role.
4. Adicionar `operations_enabled = true` dentro de `[persistence]` nos Secrets
   do Streamlit, preservando URL e chave existentes. Reiniciar o app.
5. Com contas de teste diferentes, registrar teste e pontuacao, reiniciar e
   conferir persistencia e isolamento. Reenvio da mesma evidencia/mesma missao
   nao pode duplicar pontos. Visitantes nao acumulam pontos permanentes.

Quando ativado, uma falha do banco interrompe a operacao com mensagem visivel;
nao ha gravacao silenciosa em CSV. Sem ativacao, os arquivos continuam temporarios.
Nao desativar o banco durante uma falha para simular recuperacao: isso cria
historicos divergentes. Corrigir conexao/schema e repetir o aceite.

O banco limita testes a 10.000 registros e um envio por identidade a cada dez
segundos. Isso protege o piloto, mas nao substitui protecao contra abuso publico.
Pontuacao e educativa, nao comprova entrega fisica de residuos.

## Limites e backups

- Fila limitada a 200 contribuicoes, imagem JPEG de ate 1 MB; nao enviar dataset
  completo ao banco. Originais de treinamento permanecem fora desta fila.
- Banco impoe limite e intervalo de 15 segundos por identidade; visitantes podem
  criar novas sessoes, portanto isso nao substitui login/CAPTCHA contra abuso.
- A foto e enviada antes do registro. Falha entre os dois servicos pode deixar
  arquivo orfao. Nao apagar em timeout ambiguo: verificar tabela/objeto antes de
  limpar. Auditar orfaos no console e manter margem na cota de armazenamento.
- Duplicatas por autor/hash sao recusadas pelo banco; revisoes usam comparacao
  atomica de versao. Nao importar protocolos antigos sem migracao e backup.
- Exportar aprovadas regularmente e guardar pacote com acesso restrito. Definir
  prazo de retencao e procedimento de exclusao com o grupo antes do uso amplo.
- Free tem cotas e pode pausar por inatividade. Nao ha promessa de disponibilidade
  permanente nem de gratuidade ilimitada. Acompanhar painel de uso.

Fontes consultadas em 18/09/2026:
https://supabase.com/pricing
https://supabase.com/docs/guides/platform/free-project-pausing
https://supabase.com/docs/guides/storage/security/access-control
