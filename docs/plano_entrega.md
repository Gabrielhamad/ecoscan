# Plano de entrega do EcoScan

Referência: [avaliação de 27/09/2026](avaliacao_e_entrega.md).
Metodologia: etapas sequenciais com evidência e critério de aprovação.
Responsáveis abaixo são papéis a atribuir pelo grupo, não pessoas já designadas.
Não há prazo informado; a sequência usa dependências, sem inventar datas.

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

- [ ] Confirmar o repositório correto. A pasta ecoscan deste workspace não está
      rastreada no Git pai; não adicionar o Playground inteiro.
- [ ] Revisar arquivos de código/configuração, preservando alterações existentes.
- [ ] Excluir do pacote segredos, tokens, fotos privadas, cadastros e logs pessoais.
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

Não usar somente o código de saída do aceite: ele pode retornar zero com pendências.
Revisar cada item do relatório. O aceite QA-17 de perfis locais não substitui
a validação real de autorização do Supabase.

## Etapa 3 — Fechar o experimento de visão computacional

Responsável: dados/modelagem.

- [ ] Reconciliar as 723 imagens curadas com as 672 dos splits.
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

## Registro de aceite a preencher

| Campo | Preenchimento |
| --- | --- |
| Tipo de entrega | A confirmar |
| Enunciado/critério oficial | A confirmar |
| Responsável pela aprovação | A atribuir |
| Versão/commit do código | Pendente |
| Hash e tipo do modelo | Registrados na avaliação; reconferir na release |
| Resultado automatizado | 243 execuções aprovadas após ativar processamento e evidências; ver adendo da avaliação |
| Resultado do aceite real | Pendente |
| Exceções aceitas e justificativas | A registrar |
| Data e decisão final | Pendente |

Nenhum checkbox deste plano foi marcado como concluído apenas pela existência de
um arquivo. As pendências externas permanecem visíveis até existir evidência.
