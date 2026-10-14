# Programa cidadao: territorio, aprendizagem e incentivo

Revisao: 14/10/2026. EcoScan e um piloto independente de educacao ambiental que
simula a operacao de uma secretaria. Nao e canal oficial de atendimento da
Prefeitura nem concede direitos a beneficios municipais.

## O que esta implementado

### Mapa da capital

- Diretorio parcial com 22 ecopontos nas regioes Centro, Norte, Sul, Leste e Oeste.
- Filtros por regiao e material; pesquisa por nome, bairro, rua ou CEP do ponto,
  com normalizacao de acentos e hifen. Rotas externas por endereco.
- Mapa Google My Maps publicado pela Prefeitura, carregado apenas quando
  solicitado. O mapa externo tem filtros proprios, independentes da lista local.
- Sem coordenadas locais verificadas: a lista e alfabetica, nao um ranking de
  proximidade. Nenhuma distancia ou tempo de viagem e inventado.
- General Flores permanece excluido por fechamento temporario informado na fonte.
- Aceitacao local limitada aos reciclaveis secos; nao presumimos que ecopontos
  aceitam pilhas, eletronicos, oleo ou medicamentos.

Fonte dos enderecos e situacao:
[Prefeitura, lista por subprefeitura](https://prefeitura.sp.gov.br/web/subprefeituras/w/ecoponto-esta%C3%A7%C3%A3o-de-entrega-volunt%C3%A1ria-de-inserv%C3%ADveis).
As regioes sao organizacao editorial para navegacao, nao delimitacao de rotas
de caminhões. Confirmar funcionamento e acondicionamento antes de viajar.

### CEP e coleta na rua

O ViaCEP identifica o endereco; o codigo IBGE deve ser `3550308`, municipio de
Sao Paulo. CEP inexistente, fora da capital, formato invalido ou servico
indisponivel sao tratados separadamente. Requisicao HTTPS com timeout de oito
segundos e resposta limitada; somente o CEP e transmitido, apos o clique.
Nao e salvo no perfil ou banco. A rota externa utiliza o endereco consultado
quando o usuario abre o link.

**Dias e horarios nao sao inferidos pelo CEP.** A interface oferece consultas
da Loga, Ecourbis e cata-bagulho. Pode ser necessario repetir endereco e numero
no portal. Nao ha API publica documentada integrada para importar a programacao,
nem rastreamento em tempo real. A interface informa "Horario ainda nao consultado".

Fontes: [ViaCEP](https://viacep.com.br/),
[SP Regula e concessionarias](https://prefeitura.sp.gov.br/spregula/w/residuos_solidos/residuos_solidos/domiciliar/4636),
[Loga](https://sgo3.loga.com.br/consultav2/),
[Ecourbis](https://www.ecourbis.com.br/coleta/index.html),
[cata-bagulho](https://coleta.prefeitura.sp.gov.br/).

Proxima integracao depende de contrato documentado ou autorizacao do provedor:
tipo de coleta, trecho, dias, periodo, excecoes, fonte e data de atualizacao.
Nao fazer scraping de endpoints privados nem converter dia de ecoponto em
horario de coleta domiciliar. Em falha, manter consulta oficial disponivel.

### Aprender

O catalogo `config/education.json` cobre plastico, metal, papel/papelao, vidro,
pilhas/baterias, pequenos eletronicos, oleo de cozinha e medicamentos. Para cada
material: exemplos, danos, beneficios, ciclo industrial, preparo seguro, erros
a evitar, pergunta com explicacao e fontes. Oleo e medicamentos sao orientacao
manual, nao novas classes do modelo.

Fontes institucionais e setoriais: PNUMA, SINIR, ABIPET, ABAL, Iba, Abividro,
Sabesp e Cofen; links por material no catalogo e na tela. Conteudo de processo
nao equivale a avaliacao de impacto do aplicativo. Nao converter fotos/pontos
em massa reciclada, carbono evitado ou renda sem medicao independente.

## Planejamento das missoes

| Etapa | Acao | Verificacao | Incentivo |
| --- | --- | --- | --- |
| Aprender | Ler uma rota de descarte e responder ao desafio | Resposta conferida no servidor | 10 pontos por material e conta |
| Identificar | Fotografar material que ja possui, sem risco | Analise aceita e classe compativel | Pontos da missao, uma vez por conta |
| Preparar | Separar, proteger e consultar destino | Orientacao; ainda nao comprova execucao | Sem pontos por alegacao de entrega |
| Entregar | Levar ao operador que confirme recebimento | Futuro comprovante de parceiro | Nao habilitado nesta entrega |
| Colaborar | Reportar erro ou descarte irregular | Triagem da secretaria | Sem liberacao automatica por foto |

A configuracao de referencia concentra sete missoes de identificacao. Foram
retiradas missoes que prometiam validar correcao, visita ou denuncia por uma
foto de material. As publicacoes existentes no banco nao sao sobrescritas;
analistas revisam a campanha pelo editor antes de publicar para todos.

### Pontuacao e protecao contra repeticao

- Visitante pratica, mas nao grava pontos; conta autenticada usa o extrato existente.
- Desafios possuem IDs estaveis `aprender:<material>:v1`, 10 pontos definidos no
  servidor. Resposta errada ou erro de banco nao concede pontos.
- Missao de foto consulta conclusoes anteriores e usa chave estavel de conclusao.
  A restricao unica `(user_id, mission_id, evidence_sha256)` da migration 002
  impede duas gravacoes simultaneas da mesma nova conclusao no banco.
- Nas novas transacoes, `evidence_sha256` e o hash da chave de conclusao, nao
  necessariamente da imagem. Para foto, o hash original fica identificado em
  `note`; registros antigos permanecem intactos.
- Alterar titulo/pontos nao reinicia a missao. Nao criar IDs repetidamente para
  contornar o limite. CSV local nao oferece a garantia transacional do banco.
- Isto reduz repeticao, mas nao constitui sistema antifraude para premios
  monetarios. Fotos nao comprovam limpeza, peso nem entrega.

## Recompensas disponiveis

Selos digitais nao consumiveis: Primeiros passos (50), Separacao consciente (120)
e Multiplicador EcoScan (220 pontos). Conquista calculada pelo extrato, com download
HTML acessivel e nome escapado. Nao ha debito de saldo, sorteio ou valor monetario.
O arquivo e reconhecimento informal editavel, nao certificado autenticado.

O editor da secretaria permite alterar nome, descricao, limiar e tipo. Tipo
`digital_badge` libera selo; `partner_planned` fica explicitamente sem resgate.
Recompensas antigas sem tipo assumem `partner_planned`, evitando transformar
promessa de campanha municipal em beneficio disponivel.

## Proposta de incentivos com parceiros

Priorizar oficinas de reparo/reutilizacao, visitas educativas e kits duraveis.
Mudas requerem especie, local e orientacao de cuidado. Evitar incentivo a consumo
ou coleta perigosa. Descontos em comercio ou beneficios publicos exigem acordo
formal e analise juridica; nao estao ativos.

Antes de implementar resgate: parceiro e responsavel, elegibilidade inclusiva,
validade, estoque, limite por pessoa, reserva atomica de saldo/estoque, comprovante
de entrega, cancelamento e auditoria. Definir atendimento a quem nao possui
smartphone e alternativa sem divulgar endereco, documentos ou ranking publico.
Nao contratar parceiro ou prometer recursos publicos pelo aplicativo.

## Aceite e acompanhamento

- Testes automatizados de CEP, escopo municipal, indisponibilidade, filtros,
  quiz, visitante, repeticao, falha remota, compatibilidade de recompensas e telas.
- Consulta real do CEP publico `01001-000` e navegacao em viewport de celular;
  nenhum cadastro, reporte ou ponto foi criado em producao para esses testes.
- Acompanhamento: aprendizagem antes/depois, conclusoes unicas e reportes
  respondidos. Entregas e massa somente com confirmacao do operador e consentimento.
- Horarios nativos por CEP e resgate material continuam dependencias explicitas.
