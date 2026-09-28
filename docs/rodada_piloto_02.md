# Rodada de teste: protocolos e recuperacao de falhas

Publicacao: 18/09/2026. Mesmo link do app, sem reinstalacao.

## Melhorias

- Confirmacao de envio separada da preparacao do ZIP. Falha ao baixar foto nao
  transforma um envio confirmado em erro e nao exige novo envio.
- Comprovante JSON com protocolo completo, data UTC, item e estado no envio.
  Sem identificador do autor, caminho interno, chave ou dados da equipe.
- Perfil mostra protocolos em secoes expansiveis, respostas e downloads por item.
- Indicacao de consulta ao banco concluida e aviso de identidade por sessao.
- Falha ao gravar historico local nao descarta a analise concluida.

## Aceite

1. Enviar uma correcao com foto propria autorizada.
2. Guardar comprovante e conferir o protocolo no Perfil.
3. Preparar copia com foto separadamente. Nao reenviar se apenas o download falhar.
4. Analista autenticado revisa; autor atualiza protocolos para consultar resposta.
5. Confirmar isolamento entre duas contas e persistencia apos reinicio.

Os testes automatizados simulam falhas de banco e exportacao. Nao equivalem ao
aceite completo com usuarios reais. Conta de analista usa email confirmado e lista
de autorizacao do servidor; recuperacao por link de uso unico esta implementada.
Configuracao de SMTP, template e provisionamento: [login do piloto](login_piloto.md).
Campanhas, denuncias e pontos continuam fora da migracao.
Nao houve retreinamento ou aumento de precisao declarado nesta rodada.

## Aceite complementar de autenticacao

6. Entrar com duas contas verificadas em sessoes separadas; enviar inclusive a
   mesma foto e conferir que cada conta ve apenas o proprio protocolo.
7. Sair, entrar com outra conta e conferir que analise, comprovante e pacote da
   anterior nao aparecem. Repetir apos expiracao e revogacao do papel de analista.
8. Solicitar recuperacao, abrir o email e definir nova senha. Entrar novamente e
   conferir os mesmos protocolos. A senha anterior deve ser recusada pelo provedor.
9. Reabrir o link usado e um link expirado; nenhum deve permitir alterar senha.
   Abrir o link da conta A enquanto conectado como B; o app deve encerrar B e
   alterar somente A, sem reaproveitar os dados da sessao anterior.

## Cobertura automatizada

Executar na raiz de ecoscan, com src no PYTHONPATH:

    python -m unittest tests.test_password_recovery tests.test_password_identity tests.test_pilot_02 tests.test_identity_ui tests.test_registration_and_guest tests.test_contribution_receipts_ui tests.test_contribution_store tests.test_learning_contributions tests.test_error_handling

- test_password_recovery: validacao antes de consumir link, recuperacao sem API
  administrativa, links recusados pelo provedor, falhas, limpeza da URL/sessao,
  novo login e intervalo de envio.
- test_pilot_02: duas identidades verificadas, deduplicacao por autor, bloqueio
  de revisao pelo cidadao, acesso/revogacao do analista, resposta ao autor e IDs
  preservados com novo cliente e diretorio local (reinicio simulado).
- Suites de comprovantes, persistencia e erros: consentimento, falhas de banco,
  exportacao separada do envio, conflito de revisao e falha de historico local.

Auth e armazenamento externos sao simulados nos testes. A entrega real de email,
recusa da senha antiga pelo Supabase e persistencia apos reinicio do servidor
publicado devem ser verificadas com as contas autorizadas antes de declarar o
aceite real concluido. Nenhum protocolo existente precisa ser migrado ou recriado.
