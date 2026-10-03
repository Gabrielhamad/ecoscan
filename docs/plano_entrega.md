# Plano de entrega do EcoScan

## Marco atual: controle de qualidade

Atualizacao de 03/10/2026: [quadro de entrega e validacao](controle_entrega.md).
Esse quadro orienta a sequencia atual M1-M5; as secoes datadas abaixo preservam
o historico. M1 implementado e validado localmente com 291 testes. Proximo marco:
persistencia compartilhada de campanhas e denuncias, seguido do aceite real P01-P12.
Convites dos tres analistas entregues; cadastro e login do grupo ainda a confirmar.

Referência: [avaliação de 27/09/2026](avaliacao_e_entrega.md).
Metodologia: etapas sequenciais com evidência e critério de aprovação.
Responsáveis abaixo são papéis a atribuir pelo grupo, não pessoas já designadas.
Não há prazo informado; a sequência usa dependências, sem inventar datas.

## Retomada em 29/09/2026

Ponto de partida: commit `a0cf6f2`, enviado ao GitHub, com **266 testes locais
aprovados**. O processamento preserva RGB/proporções, usa correções condicionais
e mantém a máscara como evidência. O modelo legado aguarda treino compatível;
não houve ganho de reconhecimento medido nesta entrega.

### Roteiro operacional a partir de agora

| Ordem | Entrega | Critério para avançar | Situação |
| --- | --- | --- | --- |
| 1 | Preparação de imagem e documentação | Fotos sem deformação, filtros comparados ao controle, evidências e testes | Implementado e enviado ao GitHub |
| 2 | Rastreabilidade dos reportes e aceite da publicação | Reporte registra versão do preparo/modelo; secretaria e exportação mantêm o contexto; app publicado abre e analisa uma foto de teste | Implementado e testado localmente; processamento público validado |
| 3 | Rodada coordenada do grupo | Dois participantes e um analista executam P01–P12 abaixo; protocolos persistem e não misturam contas | Pendente de contas e dispositivos reais |
| 4 | Curadoria do próximo dataset | Origem/consentimento, classe/estado e grupos de objeto/cena registrados; desconhecidos separados | Pendente |
| 5 | Novo candidato compatível | Treino nos originais, contrato v2, métricas por classe e comparação controlada; nenhum uso do teste final para ajustar | Pendente, após curadoria |
| 6 | Promoção e estabilidade | Critérios de reconhecimento aprovados, teste independente, modelo e contrato publicados juntos, versão anterior recuperável | Bloqueada pela etapa 5 |
| 7 | Fechamento do piloto | Aceite real, documentação acadêmica, retenção/backup e limites conhecidos registrados | Pendente |

Na etapa 2, não serão criadas contribuições artificiais em contas de pessoas nem
aprovadas fotos reais sem revisão autorizada. Testes locais usam dados sintéticos;
o aceite entre contas continua separado. O roteiro abaixo detalha as entregas e
responsabilidades, sem marcar como concluído aquilo que depende de validação externa.

### Evidências desta continuação

- Suíte final: **274 execuções de teste aprovadas**, incluindo contexto dos reportes,
  revisão/exportação, preservação de privacidade e persistência remota simulada.
- O Streamlit público foi reativado e processou uma prancha sintética como visitante,
  exibindo antes/depois, técnicas e aviso de modelo sem preparação compatível.
- ZIP baixado do app: 27 arquivos, manifesto de esquema 2, nove etapas, contrato
  `rgb-preserved-v2` e `mask_applied: false` na entrada RGB do classificador.
- Nenhum reporte artificial foi gravado no banco real. O teste entre participantes
  e secretaria continua na etapa 3; a simulação não substitui esse aceite.

Os novos registros guardam contexto técnico sem nomes de arquivos ou caminhos
locais, consultável pela secretaria e incluído no pacote de curadoria. Registros
antigos permanecem explicitamente sem versão conhecida. Aprovação continua sendo
revisão de rótulo, não treinamento/publicação automática.

## Etapa 1 — Fechar o escopo

Responsável: coordenação acadêmica/produto.

- [ ] Confrontar README e checklist com o enunciado oficial.
- [ ] Definir se a entrega é protótipo acadêmico, piloto real ou produto institucional.
- [ ] Confirmar as seis classes e classificação de um resíduo principal.
- [ ] Registrar se transfer learning é obrigatório ou se KNN com avaliação é aceito.
- [ ] Separar explicitamente recursos locais/experimentais do piloto persistente.

Saída: escopo aprovado pelo grupo, requisitos numerados e exclusões documentadas.
Situação atual: matriz preparada; confirmação externa pendente.

## Etapa 2 — Fixar uma versão reproduzível

Responsável: desenvolvimento e infraestrutura.

- [x] Confirmar o repositório correto: `Gabrielhamad/ecoscan`. A pasta ecoscan deste workspace não está
      rastreada no Git pai; não adicionar o Playground inteiro.
- [x] Revisar arquivos de código/configuração, preservando alterações existentes.
- [x] Excluir desta atualização segredos, tokens, fotos privadas, cadastros e logs pessoais.
- [ ] Instalar em ambiente limpo com Python 3.12 e dependências declaradas.
- [ ] Registrar versões resolvidas, commit/tag e hash do modelo selecionado.
- [ ] Executar suíte completa e aceite; guardar comando, data, ambiente e resultado.
- [ ] Testar startup do app em outro ambiente, sem depender de caminhos desta máquina.

Saída: versão identificável que outra pessoa consegue instalar e demonstrar.
A suíte atual está aprovada localmente; instalação limpa e release ainda pendentes.

Comandos de referência a partir da raiz ecoscan, com ambiente virtual ativo:

    python -m pip install -r requirements.txt
    python -m pip install --no-deps -e .
    python -m unittest discover -s tests -v
    python scripts/run_acceptance_checks.py --output reports/aceite_release
    python -m streamlit run streamlit_app.py

O aceite agora é estrito por padrão: pendências retornam código 2; falhas,
código 1. `--diagnostic` permite inspeção local sem aprovar a entrega. Revisar
cada item; QA-17 de perfis locais não substitui o aceite real QA-18 do Supabase.

## Etapa 3 — Fechar o experimento de visão computacional

Responsável: dados/modelagem.

- [x] Reconciliar a rodada antiga: 723 curadas, 672 aceitas pela preparação anterior.
- [ ] Repreparar os originais com v2 e registrar novas contagens; não assumir os mesmos 672 casos.
- [ ] Registrar origem, direitos de uso, classe e grupo de objeto/cena.
- [ ] Separar por grupos antes de aumentos artificiais; conferir duplicatas e similares.
- [ ] Reservar um conjunto realmente independente de fotos, incluindo desconhecidos,
      iluminação difícil, fundos distintos e estados dos objetos.
- [ ] Definir antes do experimento metas de macro-F1, recall por classe, cobertura,
      erro entre respostas aceitas e rejeição de desconhecidos.
- [ ] Comparar baseline e candidato no mesmo protocolo; ajustar apenas com treino/validação.
- [ ] Executar o teste final uma vez para decisão; registrar hash do modelo,
      manifesto do conjunto, parâmetros, resultados e limitações.
- [ ] Se os critérios não forem atingidos, entregar como protótipo orientativo,
      com confirmação manual, e declarar o requisito de qualidade como não atendido.

Saída: experimento reproduzível com conclusão proporcional aos resultados.
Não se exige um número arbitrário de acurácia como se estivesse na proposta.
Os limiares devem ser aprovados pelo orientador/grupo antes da validação final.

Comando já usado nesta avaliação:

    python scripts/evaluate_app_analysis.py --split test --output reports/avaliacao_release

Esse comando lê o split local existente; por si só não garante independência.
A matriz padrão não inclui a coluna de abstenção: sempre apresentar também as
respostas inconclusivas e os denominadores.

## Etapa 4 — Aceitar o piloto real

Responsáveis: infraestrutura, um analista autorizado e dois participantes.
Usar contas e fotos autorizadas; não divulgar emails, tokens ou protocolos pessoais
na documentação pública.

| Caso | Ação | Resultado exigido | Estado nesta avaliação |
| --- | --- | --- | --- |
| P01 | Criar conta A e confirmar email | Login bloqueado antes da confirmação e permitido depois | Pendente real |
| P02 | Entrar com A e enviar foto consentida | Protocolo completo e comprovante; envio único | Simulado aprovado |
| P03 | Falhar somente o download do pacote | Envio continua confirmado; repetir download sem reenviar | Simulado aprovado |
| P04 | Entrar como analista e responder | Só autorizado revisa; autor consulta resposta no mesmo ID | Simulado aprovado |
| P05 | Entrar com B e usar a mesma foto | Protocolo distinto; nenhum dado privado de A | Simulado aprovado |
| P06 | Trocar A/B, sair e expirar sessão | Sem análise, foto, formulário ou pacote residual | Simulado aprovado |
| P07 | Reiniciar/reimplantar o serviço | A/B reencontram somente seus protocolos e respostas | Pendente real |
| P08 | Recuperar senha de A enquanto B estava conectado | Sessão B limpa; senha altera somente A; IDs preservados | Simulado aprovado |
| P09 | Testar senha antiga, link expirado/reutilizado | Senha antiga e links inválidos recusados | Pendente no provedor real |
| P10 | Remover autorização do analista | Área de gestão e pacotes privados indisponíveis no próximo acesso | Simulado aprovado |
| P11 | Banco indisponível durante envio/consulta | Falha explícita; sem sucesso falso ou fallback local silencioso | Simulado aprovado |
| P12 | Abrir em celular e desktop | Toque, leitura, upload/câmera, erros e estados vazios utilizáveis | Pendente real |

Preparação: seguir [login](login_piloto.md), [banco](banco_gratuito.md) e
[rodada 02](rodada_piloto_02.md). Registrar data, versão, dispositivo, executor,
resultado e referência privada da evidência. Uma linha simulada não pode ser
promovida a aceite real sem executar o caso publicado.

Saída: todos os casos obrigatórios aprovados; qualquer falha de autorização,
perda de protocolo ou mistura de contas bloqueia a liberação do piloto.

## Etapa 5 — Empacotar e apresentar

Responsável: coordenação e mantenedor.

- [ ] Incluir README de execução, matriz de requisitos, arquitetura atual e decisões.
- [ ] Incluir relatório acadêmico com objetivo, método, dados, experimento,
      resultados, limitações, conclusão e referências.
- [ ] Anexar evidências selecionadas de teste, matriz de confusão, métricas por
      classe, contagem de abstenções, manifesto/hash do modelo e versão do código.
- [ ] Conferir exigências de formato, autoria e referências da instituição.
- [ ] Ensaiar foto válida, foto inválida, caso inconclusivo e correção/revisão.
- [ ] Demonstrar preparação, histograma, segmentação e morfologia conforme o
      [roteiro da disciplina](pratica_processamento_imagens.md), incluindo o controle
      sem operação e um caso em que a técnica piora a máscara.
- [ ] Exibir a seção pública **Processamento aplicado: antes e depois**, percorrer
      as quatro primitivas e abrir o ZIP exportado; conferir parâmetros e diferenças.
- [ ] Demonstrar claramente os perfis e o isolamento entre duas contas.
- [ ] Preparar demonstração local de contingência e explicar seus limites.
- [ ] Registrar limitações conhecidas e próximos passos, sem afirmar impacto
      ambiental medido ou acurácia não demonstrada.
- [ ] Definir responsável por backup, restauração e suporte se houver continuidade.
- [ ] Aprovar a versão final e manter procedimento de retorno sem apagar dados.

Saída: pacote revisado e apresentação coerente com o que foi demonstrado.

## Continuidade em 01/10/2026

### Concluído nesta etapa

- Validação estrita de configuração: listas, identificadores únicos, títulos,
  pontuação inteira de 0 a 10000, classes não vazias e ações conhecidas.
- Bloqueio no serviço e na interface da validação de denúncias por reconhecimento.
  Não foi implementada concessão automática de pontos após revisão de denúncia.
- Rejeição de confiança ausente, não numérica, infinita ou fora de 0 a 1.
- Resultado da missão exibido somente quando corresponde à missão selecionada.
- Suíte local: 277 testes aprovados. Não equivale a teste de produção.

Complemento da publicação: correções de missões enviadas ao GitHub (`8b3bc91`).
Identificação da revisão adicionada ao Perfil e ao contexto dos novos reportes,
com falha tolerada quando Git estiver indisponível. Suíte após esse complemento:
281 testes aprovados. Template de confirmação em português salvo no Supabase;
naquela data o envio aguardava a verificação de telefone do Brevo. Pendência
resolvida em 03/10/2026: entrega dos três convites confirmada nos logs do provedor.

### Próximas etapas e critérios de saída

1. Persistência compartilhada de campanhas e denúncias: migração aditiva,
   evidências privadas, autorização verificada no servidor e proteção contra
   edição concorrente. Reiniciar o serviço não pode perder registros.
2. Aceite integrado: duas contas de participantes e uma de analista; comprovar
   isolamento de dados, recebimento, revisão, falha de conexão e reenvio sem
   duplicação. Visitantes não devem gerar registros persistentes.
3. Curadoria e treinamento: revisar reportes, separar treino e teste sem
   duplicatas, treinar com o processamento atual e medir resultados por classe.
   Aprovar um reporte não publica um modelo automaticamente.
4. Publicação: revisar o diff, versionar, publicar e confirmar a versão executada
   no Streamlit; testar captura no celular e preservar uma versão de retorno.

Campanhas continuam em `config/campaigns.json`; denúncias e revisões continuam
em arquivos locais. Esta entrega não alterou o banco de produção nem migrou esses
registros. Não considerar a integração completa antes do aceite acima.

## Registro de aceite a preencher

| Campo | Preenchimento |
| --- | --- |
| Tipo de entrega | A confirmar |
| Enunciado/critério oficial | A confirmar |
| Responsável pela aprovação | A atribuir |
| Versão/commit do processamento | `a0cf6f2`, enviado em 29/09/2026; conferir commit final da release |
| Hash e tipo do modelo | Registrados na avaliação; reconferir na release |
| Resultado automatizado do processamento | 266 testes aprovados localmente em 29/09/2026; não equivale ao aceite real |
| Resultado do aceite real | Pendente |
| Exceções aceitas e justificativas | A registrar |
| Data e decisão final | Pendente |

Itens concluídos acima possuem evidência de execução/revisão desta atualização.
As pendências externas permanecem visíveis até existir evidência de aceite real.
