# Validacao de jornadas e dispositivos

## Camadas de evidencia

- `tests/test_user_journeys.py`: cadastro e confirmacao com provedor simulado;
  troca entre duas contas de participantes e uma de analista; isolamento de
  reportes; duplicidade; revisao por dois analistas com controle de versao;
  leitura em nova sessao; pontos por conta; destino de metal em Sao Paulo.
- A persistencia desses novos testes usa arquivos temporarios. Nao comprova
  persistencia no Supabase nem entrega de e-mail.
- Os testes existentes de PostgreSQL na CI verificam a migracao comunitaria,
  permissoes, revisoes e auditoria em banco isolado. Nao substituem homologacao
  da configuracao efetivamente publicada.
- A CI gera `reports/ci/pytest.xml` em formato JUnit e preserva o arquivo no
  artefato da execucao, inclusive quando algum teste falha.

## Inspecao publicada em 18/10/2026

Execucao local da suite completa: 415 testes aprovados, 2 ignorados e
100 subtestes aprovados. Os quatro novos cenarios de jornadas passaram.

No navegador, como visitante, foram consultados mapa e missoes com viewport
390 x 844 e perfil com viewport 1366 x 900. O mapa apresentou 22 unidades da
capital, com aviso de lista parcial. A validacao de missao ficou desabilitada
para visitante e o perfil exigiu conta verificada para contribuicoes.

A sessao aberta exibiu revisao `2efbcf064dcb`, anterior ao commit local
`f626078` usado como base desta camada. Confirmar a revisao em uma sessao nova
apos a publicacao. Uma sessao antiga aberta nao prova falha no deploy.

Esta foi uma inspecao de interface com tamanhos simulados, nao um teste em
Android/iOS fisicos. Nenhuma conta real foi criada e nenhum e-mail foi enviado.

## Homologacao real pendente

Usar duas contas de participantes e duas contas de analistas ja autorizadas.
Nao compartilhar senhas, tokens ou links de confirmacao no registro de testes.
Identificar os testes por apelidos A/B e pelo protocolo do reporte.

| Cenario | Acao | Criterio para aprovar | Estado |
| --- | --- | --- | --- |
| Cadastro | A cadastra no Android; B no computador | E-mail chega e conta nao confirmada nao entra | Pendente |
| Confirmacao | Abrir link recebido e entrar | Perfil correto; reenvio e link expirado tratados | Pendente |
| Persistencia | A envia foto com consentimento; fecha e reabre | Mesmo protocolo e imagem permanecem; B nao ve dados de A | Pendente |
| Secretaria | Analista 1 revisa; analista 2 tenta revisao antiga | Segunda revisao bloqueada; A recebe resposta | Pendente |
| Aprendizado | Aprovar contribuicao | Entra na fila de curadoria, sem retreinar/publicar automaticamente | Pendente |
| Pontos | Completar desafio, sair e entrar em outro aparelho | Saldo permanece; repetir nao duplica; B tem saldo independente | Pendente |
| Mapa | Consultar CEP publico da capital e filtrar material | Destino compativel; rota abre; nao inventa horarios de coleta | Pendente |
| iPhone | Repetir cadastro, camera e contribuicao no Safari | Permissoes, orientacao da imagem e envio funcionam | Pendente |
| Falha de rede | Interromper conexao durante envio e tentar novamente | Sem sucesso falso nem pontos/reporte duplicados | Pendente |

Registrar por execucao: revisao do aplicativo, data, sistema/navegador,
apelido da conta, cenario, resultado esperado/observado e protocolo sem dados
pessoais. Somente marcar aprovado apos observar o resultado no segundo acesso
e, quando aplicavel, na secretaria. Uma aprovacao local nao aprova producao.

## Executar localmente

```shell
python -m pytest tests/test_user_journeys.py -q
python -m pytest tests -q --junitxml=reports/ci/pytest.xml
```
