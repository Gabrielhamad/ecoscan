# Recuperacao operacional do piloto

## Escopo e responsabilidade

Preparacao do marco M5. O verificador local detecta alteracoes em uma copia ja
exportada; **nao exporta dados, nao restaura o Supabase e nao comprova que a copia
esta completa**. Um SQL vazio de tabelas pode passar no teste de integridade.
O aceite exige restauracao isolada e verificacao funcional por outro integrante.

O responsavel pela infraestrutura deve autorizar e executar a copia privada.
Nunca anexar banco, manifesto com nomes de arquivos, fotos, emails, tokens ou
chaves ao GitHub. `backups/` esta ignorado pelo Git, mas isso nao criptografa dados.
Usar destino com acesso restrito e criptografia; a chave de recuperacao deve ficar
separada. Nao exportar dados de producao para uma maquina de colega sem autorizacao.

## Inventario obrigatorio

| Componente | O que preservar e conferir |
| --- | --- |
| Banco da aplicacao | `ecoscan_contributions`, `ecoscan_points`, `ecoscan_field_tests`, `ecoscan_campaigns`, `ecoscan_civic_reports`, `ecoscan_community_audit`; esquema, dados, funcoes, gatilhos, sequencias, RLS e permissoes |
| Fotos privadas | Objetos dos buckets `ecoscan-contributions` e `ecoscan-civic-evidence`; banco nao substitui arquivos do Storage |
| Identidade | Plano especifico de recuperacao do Supabase Auth e vinculos de UUID; recriar usuarios pode quebrar os vinculos existentes |
| Versao | SHA completo do Git, migracoes aplicadas, configuracao e modelo ativo com contrato de processamento |
| Servicos externos | Configuracoes de Auth, redirecionamentos, SMTP e flags; segredos em cofre separado, nunca neste pacote |

O procedimento de exportacao/restauracao deve ser escolhido de acordo com os
recursos efetivamente disponiveis na conta Supabase. Nao presumir backup
automatico, retencao ou recuperacao pontual no plano gratuito. O pacote abaixo
cobre arquivos exportados, nao constitui por si so recuperacao integral de Auth.

## Preparar e verificar a copia

1. Registrar responsavel, horario, SHA, migracoes e contagens por tabela/bucket
   em registro privado. Definir uma janela sem novas gravacoes; o verificador
   nao cria snapshot consistente entre PostgreSQL e Storage.
2. Exportar banco e objetos por ferramenta autorizada, preservando nomes/chaves.
   Conferir referencias de fotos no banco contra objetos existentes. Registrar
   orfaos separadamente, sem excluir automaticamente.
3. Organizar o pacote concluido, sem arquivos em escrita, assim:

```text
backups/<identificador-privado>/
  database.sql
  storage/
    ecoscan-contributions/
    ecoscan-civic-evidence/
  operation.json             Registro privado de versao e contagens
```

Os diretorios de ambos os buckets sao obrigatorios, mesmo vazios. `operation.json`
e os demais documentos extras sao incluidos no hash, mas seu conteudo nao e
validado automaticamente. O SQL deve estar em formato texto apropriado ao
procedimento de restauracao escolhido; o verificador nao interpreta SQL.

```powershell
python scripts/check_backup.py seal backups/<identificador-privado> --revision <SHA-completo>
python scripts/check_backup.py verify backups/<identificador-privado>
```

`seal` grava `integrity.json` sem sobrescrever um manifesto existente. `verify`
recalcula SHA-256 e tamanho de todos os arquivos e rejeita arquivos ausentes,
adicionais, alterados ou links. Executar novamente depois de transportar a copia.
Saida 0 significa integridade verificada; saida 1, falha. Nao recriar o manifesto
para esconder uma divergencia: investigar e gerar outra copia identificada.
O manifesto nao e assinatura digital nem protege contra quem pode adulterar
simultaneamente arquivos e manifesto. Proteger o conjunto contra modificacoes.

## Ensaio isolado de recuperacao

1. Criar ambiente isolado, com custos previamente aprovados e envio de emails
   desativado. Nunca ensaiar restauracao sobre a producao.
2. Conferir hashes; restaurar esquema e dados com procedimento revisado e
   recuperar objetos privados. Conferir Auth e preservar os vinculos de dono.
3. Comparar contagens, referencias, hashes das fotos, sequencias e auditoria.
   Conferir buckets privados e negacao de acesso anonimo/direto.
4. Executar P01-P12 com contas de teste autorizadas: visitante nao grava;
   participante ve somente seus registros; analista revisa; outra conta nao
   consegue ler foto privada; campanha e resposta sobrevivem ao reinicio.
5. Registrar tempo, perdas observadas, falhas e evidencias privadas. Aprovacao
   por outro integrante e obrigatoria antes de encerrar M5.

## Atualizacao, retorno e incidente

Antes de publicar: suite e CI aprovadas, SHA anterior registrado, copia verificada
quando houver mudanca de dados e migracao aditiva revisada. Publicar codigo,
modelo e contrato de processamento em conjunto quando aplicavel. Conferir no
app a revisao implantada e um fluxo curto de leitura/login/gravacao autorizada.

Se houver regressao, suspender o fluxo afetado e voltar ao commit conhecido por
reversao revisada, sem reescrever historico e sem apagar tabelas. Conferir se o
codigo anterior aceita o esquema atual. Restaurar backup e operacao diferente:
pode perder registros posteriores e exige autorizacao e conciliacao antes.

Em incidente de acesso, bloquear o acesso indevido, revogar credenciais afetadas
e preservar evidencias privadas. Nao publicar logs sensiveis para diagnostico.
Definir com o grupo prazo de retencao/exclusao, responsavel, perda maxima de
dados toleravel (RPO) e tempo toleravel de recuperacao (RTO); ainda nao medidos.

## Criterio de conclusao

- Ferramenta testada com dados sinteticos: preparacao tecnica.
- Backup real autorizado e conferido: pendente.
- Restauracao isolada, identidade, Storage e P01-P12: pendentes.
- Retencao, RPO/RTO, responsavel e revisao por segunda pessoa: pendentes.

Nenhum backup real e executado automaticamente por este documento ou script.
