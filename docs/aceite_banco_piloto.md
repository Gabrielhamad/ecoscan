# Aceite de banco do piloto

Verificacao realizada em 20/09/2026. Este documento nao declara aceite de producao.

## Evidencias confirmadas

- Migration 002 executada com sucesso no projeto Supabase do EcoScan.
- Tabelas `ecoscan_points` e `ecoscan_field_tests` com RLS ativo.
- `anon` e `authenticated` sem privilegio SELECT direto nas duas tabelas.
- `service_role` com INSERT nas duas tabelas; chave restrita ao servidor.
- Teste SQL sob `service_role`: INSERT e SELECT retornaram um registro em cada
  tabela; transacao revertida, sem manter dados sinteticos no banco.
- `operations_enabled = true` salvo na secao persistence dos Secrets do Streamlit.
- Suite local da versao 6875b77: 177 testes aprovados.

## Pendencias de aceite ponta a ponta

- Confirmar carregamento da versao 6875b77 ou superior no processo Streamlit.
- Supabase Authentication nao possui usuarios no momento desta verificacao.
  Provisionar conta com email verificado e validar entrada/saida antes de liberar
  pontuacao permanente. Nao marcar email como confirmado sem verificar.
- Autorizar explicitamente o email do analista nos Secrets; a lista de emails
  nao cria conta, nao confirma email e nao define senha.
- Com duas contas reais, testar registro, reinicio, consulta de historico,
  isolamento e revisao por analista. SQL e testes com mocks nao substituem isso.
- Enviar uma foto consentida pelo app, receber protocolo, revisar na secretaria,
  consultar resposta como autor e exportar apenas aprovadas para treino candidato.

## Limites que permanecem

- Denuncias e suas evidencias ainda usam arquivos locais temporarios.
- Campanhas permanecem configuradas em arquivo, sem publicacao dinamica no banco.
- Cadastro/recuperacao de senha e provisionamento devem seguir login_piloto.md;
  nao disparar convites antes de validar o callback de definicao de senha.
- Treino de candidatos ocorre fora da hospedagem. Aprovacao de uma foto nao
  publica modelo nem comprova aumento de acuracia.
- O classificador atual continua em avaliacao; esta migracao nao o retreina.

## Operacao

Nao reverter para CSV para esconder indisponibilidade do banco. Investigar a
falha e preservar historico. Nao salvar chaves no repositorio. Antes de ampliar
o grupo, fechar os itens de aceite e definir responsavel por revisao, retencao
de fotos, backup e publicacao de modelos.
