# Aceite do ambiente publicado

Este roteiro valida a aplicação implantada. Testes locais e simulação de `User-Agent`
não substituem a execução em um aparelho real.

## Aceite de contas e contribuições — 04/11/2026

No código funcional `0ad6ed7`, o app público passou em cadastro e confirmação de
duas contas, login/logout, protocolo persistente da conta A, isolamento para B,
revisão por analista autorizado e resposta persistente visível somente para A.
A CI correspondente é o [run 48](https://github.com/Gabrielhamad/ecoscan/actions/runs/41894070190).
Nenhum dado de conta, foto, token ou protocolo foi anexado à evidência.

Também passaram: retirada temporária do analista da allowlist, migration 004 e
constraints validadas, buckets privados, relato cívico, pontos sem duplicação e
teste de campo com isolamento. Permanecem o ensaio de indisponibilidade e a
recuperação de backup em janela controlada.

## Registro obrigatório

Antes de testar, registre:

- URL e hash do `main` implantado;
- data, horário e responsável;
- dispositivo, sistema, navegador e tipo de conexão;
- perfil usado: visitante, participante ou gestão;
- resultado, tempo percebido, mensagem de erro e captura sem dados pessoais.

Use os estados `aprovado`, `reprovado` ou `bloqueado`. Um item bloqueado não conta
como aprovado.

## Matriz mínima

| Ambiente | Jornada | Critério |
| --- | --- | --- |
| Computador, janela anônima | Abrir como visitante | Primeira tela aparece sem recarregar manualmente |
| Android, Chrome | Abrir e capturar foto | Permissão, prévia e análise funcionam |
| iPhone, Safari | Abrir e capturar foto | Permissão, prévia e análise funcionam |
| Participante | Cadastro, confirmação e login | Sessão sobrevive a uma atualização de página |
| Duas contas | Protocolos e contribuições | Uma conta não acessa registros da outra |
| Gestão autorizada | Revisão e resposta | Visitante e participante não acessam a área |

## Jornada pública

1. Abrir `https://ecoscan-gabrielhamad.streamlit.app` em janela anônima.
2. Medir até a primeira tela utilizável e registrar se apareceu tela branca.
3. Navegar por educação, descarte e pontos de coleta.
4. Enviar uma foto de garrafa PET, lata ou embalagem de vidro.
5. Confirmar que a hipótese aparece como assistida e exige confirmação humana.
6. Repetir com arquivo vazio, corrompido, formato inválido e foto fora do escopo.
7. Confirmar que nenhuma falha expõe caminho local, token ou detalhe interno.

## Jornada de conta e gestão

1. Criar duas contas de teste com endereços controlados.
2. Confirmar e-mail, entrar, sair e recuperar acesso.
3. Criar um protocolo em cada conta e atualizar a página.
4. Verificar isolamento entre as contas e persistência após novo login.
5. Entrar com uma conta de gestão autorizada, revisar e responder um registro.
6. Confirmar que a resposta aparece somente para a conta responsável.

## Desempenho e estabilidade

Em cada dispositivo, executar três aberturas: primeira visita, atualização e retorno
após cinco minutos. Registrar tempo até uso, falhas, recarregamentos e estado da
sessão. Como meta inicial de piloto:

- primeira tela utilizável em até 5 segundos em conexão estável;
- atualização em até 3 segundos;
- nenhuma tela branca permanente;
- nenhum loop de login;
- análise inválida não derruba a sessão.

## Evidência técnica desta revisão

Em 04/11/2026, o ambiente de engenharia confirmou o servidor local e o endpoint
`/_stcore/health`. A renderização local ficou abaixo de 0,6 segundo na primeira
execução e próxima de 0,01 segundo nas atualizações.

O proxy de auditoria bloqueou `*.streamlit.app` com HTTP 403 antes da negociação
TLS. Esse resultado não veio do EcoScan e não aprova nem reprova o deploy público.
O teste externo encontrou, pela CI, uma dependência de processamento ausente em
instalações limpas. A correção foi reproduzida em ambiente novo com 450 testes e
96 subtestes aprovados.

O primeiro marco só pode ser encerrado depois que a matriz mínima for executada
em aparelhos reais e o hash testado tiver CI verde.

## Resultado do smoke test público

Execução de 04/11/2026 sobre o código funcional `16344df`:

| Ambiente | Resultado | Evidência informada |
| --- | --- | --- |
| Computador, janela anônima | Aprovado | Aplicação abriu e concluiu a análise de uma foto |
| Android | Aprovado | Abertura, câmera e análise confirmadas em aparelho real |
| iPhone | Aprovado | Abertura, câmera e análise confirmadas em aparelho real |
| GitHub Actions | Aprovado | [Execução 46](https://github.com/Gabrielhamad/ecoscan/actions/runs/41891056500) concluída com sucesso |

Este resultado aprova a jornada pública de visitante nos três tipos de dispositivo.
Cadastro, isolamento entre contas, gestão e persistência continuam pendentes do
aceite integrado com o Supabase.
