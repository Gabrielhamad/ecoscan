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
aceite completo com usuarios reais. Conta de analista e recuperacao de senha ainda
precisam ser concluidas. Campanhas, denuncias e pontos continuam fora da migracao.
Nao houve retreinamento ou aumento de precisao declarado nesta rodada.
