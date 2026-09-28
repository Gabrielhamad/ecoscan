# Avaliação do EcoScan e decisão de entrega

Data: 27/09/2026. Avaliação local; não certifica a implantação publicada.

## Parecer

O projeto está alinhado à proposta documentada de um **piloto acadêmico de
processamento de imagens, classificação orientativa de um resíduo principal,
educação ambiental e revisão humana**. Não há evidência suficiente para declarar
o piloto real concluído ou liberar uso institucional como reconhecimento confiável.

Esta avaliação usa README, checklist da APS, configuração ativa e roteiro do
piloto 02. O enunciado oficial da instituição não foi apresentado nesta conversa:
a conformidade com exigências externas de nota, formato e arquitetura deve ser
confirmada pelo grupo. Entrega acadêmica é a hipótese de trabalho.

A decisão depende do tipo de entrega:

| Entrega | Parecer | Condição |
| --- | --- | --- |
| Demonstração acadêmica do protótipo | Apta com ressalvas | Apresentar os resultados e limitações desta avaliação; conferir enunciado oficial |
| Piloto 02 declarado como concluído com usuários reais | Não aprovado ainda | Executar aceite real de email, analista, duas contas e reinício na implantação |
| Modelo final com desempenho validado | Não aprovado ainda | Avaliação independente e critérios quantitativos definidos antes do experimento |
| Uso institucional amplo | Não aprovado | Resolver persistência dos fluxos prometidos, operação, segurança e validação real |

## Metodologia aplicada

Foi adotada uma sequência de cinco etapas com rastreabilidade entre requisito,
implementação, evidência e decisão. Não é uma certificação de norma.

1. **Fixar a proposta:** identificar objetivo, seis classes ativas e itens fora do
   MVP; distinguir intenção futura de funcionalidade existente.
2. **Inspecionar a implementação:** verificar arquitetura, identidade, persistência,
   seleção de modelo, preparação dos dados e documentação.
3. **Executar verificações:** suíte completa, aceite local, inventário dos dados,
   comparação de hashes entre splits e avaliação do pipeline atual.
4. **Classificar as evidências:** verificado localmente, parcial, não verificado
   externamente ou fora de escopo. Ausência de arquivo não equivale sempre a defeito;
   existência de arquivo não prova qualidade nem aceite.
5. **Preparar a entrega:** registrar bloqueadores, responsáveis por papel e
   critérios de saída no [plano de entrega](plano_entrega.md).

## Matriz de conformidade

| ID | Requisito da proposta | Evidência examinada | Resultado |
| --- | --- | --- | --- |
| R01 | Foto por upload e captura | UI, testes de imagem/câmera e aceite QA-03/05 | Verificado localmente; câmera de aparelho real pendente |
| R02 | RGB, preparação, filtros e segmentação observáveis | pipeline, metadados e QA-06 | Verificado localmente |
| R03 | Classificação de um resíduo principal | modelo KNN visual carregado e avaliação atual | Implementado; qualidade depende dos resultados abaixo |
| R04 | Orientação independente do classificador | configuração de descarte, testes e QA-02/12/13 | Verificado estrutural e funcionalmente; fontes não reauditadas nesta rodada |
| R05 | Visitante, participante e analista | testes de identidade, piloto 02 e revisão | Verificado com Auth simulado; contas reais pendentes |
| R06 | Recuperação de senha sem trocar propriedade | serviço, callback e testes de recuperação | Implementado; SMTP e troca real no provedor pendentes |
| R07 | Envio consentido, protocolo, resposta e isolamento | testes de contribuição, comprovantes e piloto 02 | Verificado com banco/storage simulados |
| R08 | Persistência após reinício | novo cliente e diretório local nos testes | Reinício simulado; implantação real pendente |
| R09 | Dataset separado e rastreável | inventário e hashes dos seis grupos ativos | Sem duplicatas binárias entre splits; separação por objeto/cena não comprovada |
| R10 | Métricas, matriz e relatório | avaliações históricas e nova avaliação | Existentes; relatórios históricos não representam automaticamente a versão atual |
| R11 | Coleta, missões e denúncias | configurações, serviços e QA-15/16 | Parcial para operação real; denúncias/campanhas ainda locais |
| R12 | Execução reproduzível e entrega versionada | requirements, runtime e estado Git local | Parcial; dependências variáveis e pasta local sem rastreamento no Git pai |
| R13 | Detecção treinada de vários objetos | contrato desativado e documentação | Fora do MVP; não anunciar como entregue |

## Evidências executadas

- Suíte completa: **216 execuções, zero falhas**, em 11,326 segundos na execução
  concluída. A descoberta inclui classes de teste importadas em outros módulos;
  esse número não representa cobertura percentual nem 216 cenários independentes.
- A primeira captura não apresentou resumo final; a execução foi repetida com
  identificação dos testes e diagnóstico de bloqueio. O resultado citado é o da
  execução concluída, cujo log foi preservado.
- Aceite local: **14 ok, 2 em atenção, 1 pendente, zero falhas**.
- Atenções do aceite: cadastro de coleta cobre quatro das seis classes e o
  verificador de interface é baseado em marcadores de código, sem inspeção visual.
- Pendência do aceite: arquivo final de transfer learning ausente.
  Isso não impede demonstrar KNN; impede declarar o artefato Keras como entregue.
- Smoke de inferência e análise de frame executados. Isso não testa câmera física,
  navegador móvel, rede nem latência de uma transmissão real.

Ambiente observado: Windows, Python 3.14.5, NumPy 2.4.4, Pillow 12.2.0,
Streamlit 1.57.0, OpenCV 5.0.0.93, scikit-learn 1.9.1 e scikit-image 0.26.0.
O SDK Supabase não está instalado nesse Python; os testes externos usam simulações.
Portanto, esse resultado não substitui instalação limpa com as dependências do
projeto e Python 3.12 recomendado.

Evidências locais desta rodada ficam em
[reports/avaliacao_entrega_2026-09-27](../reports/avaliacao_entrega_2026-09-27/).
Essa pasta fica em área de relatórios; revisar sua inclusão explícita no pacote
da entrega, pois relatórios podem ser ignorados no Git. Não empacotar toda a pasta
reports, logs, fotos ou dados de usuários indiscriminadamente.

## Dados e reconhecimento

| Classe | Brutas | Curadas | Treino | Validação | Teste |
| --- | ---: | ---: | ---: | ---: | ---: |
| Plástico | 150 | 140 | 85 | 18 | 19 |
| Papel/papelão | 150 | 147 | 96 | 21 | 20 |
| Metal | 150 | 143 | 94 | 20 | 20 |
| Vidro | 149 | 145 | 92 | 20 | 20 |
| Pilhas/baterias | 78 | 72 | 50 | 11 | 10 |
| Eletrônicos | 79 | 76 | 53 | 11 | 12 |
| Total | 756 | 723 | 470 | 101 | 101 |

O split soma 672 imagens, abaixo das 723 curadas. Isso exige reconciliar o
manifesto e justificar as 51 imagens de diferença; não é prova isolada de perda.
Nenhum hash de arquivo se repetiu entre treino, validação e teste nas classes
ativas. O algoritmo de split agrupa hashes iguais, mas não recebe um identificador
de objeto/cena: fotos diferentes do mesmo objeto ainda podem cruzar os conjuntos.

Modelo selecionado: models/vision_classifier.npz (KNN visual).
SHA-256: ae827295b13a6a6a8f330343a090cdc12c49f14fd1bb25ada52cb1b5d4a855fe.
Configurar MobileNetV2 no JSON não significa que esse modelo esteja em uso.

Relatórios anteriores, como app_analysis_professional_v4, incluem 12 classes e
146 imagens; não devem ser apresentados como desempenho das seis classes atuais.
A avaliação desta rodada usa o split local existente, que já participa do histórico
do projeto; não há comprovação de conjunto cego independente. Não ajustar o modelo
sobre esse teste e depois usar o mesmo resultado como validação final.

A avaliação inicial (seleção adaptativa, antes do padrão didático ativo) concluiu
com código de saída 0 em **101 imagens**:

| Indicador | Resultado |
| --- | ---: |
| Acerto sobre todas as imagens (abstenções contam como não acerto) | 47/101 = 46,53% |
| Macro-F1 | 0,5285 |
| Respostas inconclusivas | 31/101 = 30,69% |
| Respostas aceitas | 70/101 = 69,31% |
| Acerto entre as respostas aceitas | 47/70 = 67,14% |
| Respostas aceitas incorretas | 23/70 = 32,86% |

| Classe | Precisão | Recall | F1 | Amostras |
| --- | ---: | ---: | ---: | ---: |
| plastic | 52.94% | 47.37% | 0.5000 | 19 |
| paper_cardboard | 66.67% | 40.00% | 0.5000 | 20 |
| metal | 66.67% | 60.00% | 0.6316 | 20 |
| glass | 84.62% | 55.00% | 0.6667 | 20 |
| battery | 75.00% | 30.00% | 0.4286 | 10 |
| electronic | 66.67% | 33.33% | 0.4444 | 12 |

Esses resultados sustentam uma demonstração orientativa com limitações explícitas,
mas não uma afirmação de reconhecimento confiável para uso institucional. Em especial,
pilhas e eletrônicos tiveram recall de 30,00% e 33,33%. Não houve melhora por treino
nesta rodada: apenas medição do código e do artefato já existentes.

Evidência: [métricas atuais](../reports/avaliacao_entrega_2026-09-27/modelo_atual/metrics.json).
A matriz original omite abstenções; uma tabela complementar com essa coluna foi
salva junto às evidências. O teste inclui somente classes ativas e não quantifica
a rejeição de objetos desconhecidos.

## Achados por prioridade

| ID | Prioridade | Achado e impacto | Ação de saída |
| --- | --- | --- | --- |
| A01 | Alta | Cadastro, recuperação, revisão e isolamento ainda sem evidência desta avaliação na nuvem real | Aceite de duas contas e um analista, SMTP e reinício, com protocolo preservado |
| A02 | Alta | Qualidade do modelo final não comprovada; avaliações antigas usam outro escopo | Registrar métrica atual, estabelecer meta e avaliar em conjunto independente |
| A03 | Alta | Split sem agrupamento por objeto/cena; diferença entre curadas e splits | Manifesto reconciliado e grupos de origem, sem parentes entre splits |
| A04 | Alta para piloto durável | Campanhas e denúncias usam arquivos locais | Migrar os fluxos prometidos ou explicitá-los como demonstração local |
| A05 | Alta para liberação | A pasta ecoscan aparece como não rastreada no Git pai consultado | Confirmar repositório de entrega, revisar arquivos e produzir versão identificável |
| A06 | Média | Relatórios de prontidão contêm aprovação fixa ou por existência de arquivo | Usar a matriz desta avaliação; revisar os geradores antes de tratá-los como certificação |
| A07 | Média | Ambiente testado diverge do recomendado e não tem SDK Supabase | Instalação limpa, versões registradas e smoke de integração |
| A08 | Média | Câmera, acessibilidade, fontes de coleta e operação sem validação atual de campo | Ensaio em celular/desktop e conferência de fontes oficiais |
| A09 | Média para uso amplo | Backup/restauração, retenção, exclusão e resposta a incidentes sem evidência operacional | Definir responsáveis e demonstrar restauração sem apagar protocolos |

A06 tem evidência concreta: aps_audit usa existência de arquivos em vários gates;
delivery_pack marca cenários como ok sem executá-los; final_readiness contém
status ready fixo para operação. Esses relatórios ajudam a organizar o trabalho,
mas seu percentual não é um percentual de qualidade ou conformidade da solução.

A05 refere-se somente a este checkout local. Não foi inferido que o repositório
remoto esteja vazio ou que a versão publicada coincida com esta pasta.

## Limites desta avaliação

Não houve implantação, alteração de banco, criação de conta, envio de email,
retreinamento ou substituição do modelo. Não foram auditados todos os caminhos
de segurança nem validadas licenças de cada imagem. O aceite humano e o enunciado
oficial continuam necessários para declarar a entrega final aprovada.

## Adendo: práticas de processamento

**Estado em 28/09/2026:** o perfil padrão do aplicativo passou a ser adaptativo
para coincidir com a preparação usada no treino SVM. Os números abaixo são
históricos e se referem ao perfil didático mediana/Otsu da rodada anterior;
não representam o desempenho do perfil adaptativo atual.

Após esta avaliação, foram integrados controles de morfologia binária, máscaras
antes/depois, histogramas e experimento sintético. Consulte o
[roteiro prático](pratica_processamento_imagens.md). Os números de reconhecimento
acima pertencem à avaliação anterior; esta implementação não declara ganho de
acurácia. Em seguida, o padrão didático foi ativado: mediana 3×3, Otsu e
abertura + fechamento 3×3, com antes/depois de cada primitiva e exportação PNG/ZIP.
O controle sem operação continua selecionável. O classificador recebe a imagem
com a máscara final; isso é verificado nos testes, e não apenas declarado na UI.

A nova regressão passou em **243 execuções, zero falhas**, em 14,081 segundos.
Inclui identidade, recuperação, isolamento, protocolos e os novos testes de evidência.
Não houve alteração de registros de usuários, protocolos ou credenciais.

### Efeito do novo padrão, sem retreinamento

O mesmo modelo e split local de 101 imagens foram avaliados; os parâmetros foram
fixados antes da medição e não ajustados a partir desses resultados.

| Indicador | Avaliação inicial | Padrão didático ativo |
| --- | ---: | ---: |
| Acertos / total | 47/101 (46,53%) | 48/101 (47,52%) |
| Macro-F1 | 0,5285 | 0,5293 |
| Inconclusivos | 31/101 | 25/101 |
| Respostas aceitas | 70/101 | 76/101 |
| Acertos entre aceitas | 47/70 (67,14%) | 48/76 (63,16%) |
| Erros entre aceitas | 23/70 (32,86%) | 28/76 (36,84%) |

Não se conclui ganho de qualidade: embora haja um acerto adicional, há cinco
erros aceitos adicionais e queda na proporção de acertos entre respostas aceitas.
A mudança satisfaz a demonstração das operações, mas exige validação específica
para uso operacional. O modelo continua orientativo, com revisão humana.
As limitações do conjunto de teste e do aceite em nuvem permanecem.

Evidências: [nova avaliação](../reports/processing_applied_2026-09-27/evaluation/metrics.json),
[prancha de foto real](../reports/processing_applied_2026-09-27/foto_real/antes_depois.png)
e [log de testes](../reports/processing_applied_2026-09-27/tests.log).
