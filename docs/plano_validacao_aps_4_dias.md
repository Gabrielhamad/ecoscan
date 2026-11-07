# Plano de validação técnica da APS — 7 a 11/11/2026

**Objetivo:** transformar a versão atual do EcoScan em **entrega acadêmica executável, demonstrável e verificável**, com resultados verdadeiros e relatados, sem prometer reconhecimento perfeito.

**Baseline auditado:** `main` `37f778db02230a601163f8a1c7b07d8954b431ff`.  
**Data-limite informada:** 11/11/2026.  
**Referência recebida do grupo:** `ManualAPS-5oe6oCCI-PI-2026 2.pdf`, cujo cabeçalho interno apresenta **2025/2**. Conferir se há atualização da professora para o semestre vigente.  
**Natureza:** o manual pede a produção de um **programa**, não exige por si só um binário Windows `.exe`. Não afirmar que há instalador desktop sem criá-lo e testá-lo.

## 1. O que é obrigatório demonstrar na APS

| Requisito do manual | Implementação no projeto | Evidência da entrega |
| --- | --- | --- |
| Problema e sustentabilidade | Identificação assistida e descarte adequado de resíduos | Introdução com problema, contexto, objetivos e caso real |
| Aquisição | `image_processing/image_io.py`; câmera/upload Streamlit | Arquivo real, formato/dimensões, tratamento RGB/EXIF |
| Manipulação | `image_processing/preprocessing.py`; `app/pipeline.py` | Original, pré-processamento e entrada preservada |
| Filtragem | `image_processing/filters.py` | **Duas ou mais** comparações antes/depois em fotos reais, parâmetros, benefícios e falhas |
| Segmentação | `segmentation/methods.py` e `segmentation/morphology.py` | Máscara Otsu/HSV e comparação morfológica, inclusive limitações |
| Modelo de visão | `classification/semantic_onnx.py` e `services/recognition_safety.py` | Explicar escolha, classes, inferência, confirmação humana e métricas |
| Desenvolvimento/testes | `tests/`, GitHub Actions, scripts e evidências de processamento | Testes reais reproduzíveis, casos válidos e inválidos, resultados medidos |
| Relatório | Documento acadêmico específico da APS | Introdução, referencial, proposta, desenvolvimento, conclusão, bibliografia, apêndice de código, ficha APS |
| Apresentação | Programa funcionando | Seminário de 10–15 minutos com demonstração e análise de resultados |

O manual de referência não estabelece percentual mínimo de acurácia do reconhecedor nem a obrigação de empacotamento `.exe`. O nível de refinamento, a funcionalidade e o tratamento de erros pesam na qualidade da implementação. Usar exatamente os requisitos adicionais comunicados pela professora, quando existirem.

**Autores e formatação:** no arquivo acadêmico final, nomes e RAs reais; fonte Arial 12, espaçamento 1,5, margens esquerda/direita 2,5 cm, papel A4 conforme o manual recuperado. Confirmar plataforma de postagem e cronograma com a professora. Não publicar nomes/RAs, fotos privadas ou credenciais na issue pública.

## 2. Condições técnicas para declarar a demonstração pronta

| ID | Teste | Critério proposto de aceite | Registro mínimo |
| --- | --- | --- | --- |
| T01 | Instalação limpa | Python 3.12, instalação declarada, inicialização sem erro na máquina da apresentação | SO, Python, comando, SHA, resultado |
| T02 | Início e ausência de rede | App inicia e o fluxo principal funciona no ambiente confirmado, ou há alternativa de execução **previamente testada** | Tempo real medido, evidência e plano de contingência |
| T03 | Entrada válida | Imagem JPG/PNG e foto de câmera são exibidas corretamente em RGB, sem rotação ou corte inesperado | Capturas e dimensões |
| T04 | Entrada inválida | Arquivo vazio/corrompido/não imagem é recusado sem tela branca, informação privada ou queda da sessão | Mensagem e resultado |
| T05 | Filtros reais | Pelo menos filtro mediana e gaussiano ou Sobel em fotos reais, comparados ao controle, exibem operação, parâmetros e resultado | Original, output, interpretação |
| T06 | Segmentação real | Otsu e outro método exibem máscaras e apresentam explicação dos erros de fundo, sombra e objeto | Máscaras antes/depois e descrição |
| T07 | Morfologia | Demonstração explícita de erosão, dilatação, abertura ou fechamento com efeito e kernel conhecidos | Imagens/IoU se existir referência anotada |
| T08 | Rastreabilidade PDI | Exportação de ZIP/JSON de evidências usa **a mesma imagem e operações executadas**, sem inventar melhoria do reconhecimento | ZIP, manifesto, SHA e parâmetros |
| T09 | Inferência | ONNX carrega no dispositivo de demonstração, retorna sugestão ou rejeição controlada sem erro fatal; quando errado, usuário pode corrigir | Registro de acerto/erro/rejeição sem ocultá-los |
| T10 | Regra de descarte | Para **todas as classes confirmadas manualmente**, exibe destino e cor corretos; pilha/eletrônico seguem coleta especial | Cenários por classe (100% esperado para regra determinística) |
| T11 | Navegação e estado | Alternar abas não perde captura/sessão ou expõe área de gestão ao visitante | Teste de UI e dispositivo real |
| T12 | Regressão/CI | `ruff`, `pytest`, `pip check` e PostgreSQL verdes no SHA escolhido | URL da CI |
| T13 | Dispositivos | Navegação e captura no computador e celular real, sem depender só da simulação de navegador | Modelo do dispositivo, navegador e resultado |
| T14 | Demonstração completa | Roteiro de 10–15 minutos funciona três vezes em sequência; plano B de foto previamente autorizada | Ensaio com cronômetro e ocorrências |
| T15 | Entrega final | Documento ABNT, apêndice de código, ficha cronológica APS e upload/entrega conforme orientação vigente | Arquivo final, comprovante e responsável |

T01–T15 são **critérios sugeridos para esta entrega**, não números ou casos oficialmente exigidos pelo manual.

### Limitação importante do verificador do repositório

O script `scripts/run_acceptance_checks.py` (sem `--diagnostic`) exige todos os status `QA-01..QA-21` como `ok`. Entretanto o código **marca `QA-09` (aceite independente do modelo) e `QA-18..QA-21` (contas, persistência, dispositivos e recuperação) como `pending`**, pois dependem de evidências manuais externas. Portanto, ele tende a retornar **2 (aceite incompleto)** mesmo com a CI verde. O modo `--diagnostic` não é aprovação de release. Não alterar status falsamente nem desativar esses testes para fabricar aprovação: registrar a evidência manual e separar o Gate Acadêmico do Gate Institucional.

## 3. Validação rápida do reconhecimento no mundo real

**Coleta proposta para 4 dias:** começar por **10–15 objetos físicos diferentes por classe prioritária** (metal, plástico, vidro; 30–45 objetos), preferencialmente 1 foto por objeto para a métrica principal, mais 5–10 exemplos de casos difíceis/fora do escopo. Se puder, usar mais de um celular. Isso serve como diagnóstico acadêmico inicial, **não como certificação estatística de produção**.

Para cada foto: rótulo real conferido, `object_id`, `session_id`, iluminação/fundo, hash SHA-256, classe sugerida, aceita/rejeitada, classificador correto/incorreto, confirmação humana e sucesso das operações PDI. Fotos do mesmo objeto não devem ser contadas como objetos independentes.

- Congelar as fotos de teste e os hashes **antes** de medir; não ajustar o modelo nesses próprios exemplos e depois chamar isso de teste independente.
- Executar `scripts/validate_semantic_onnx.py` conforme `docs/avaliacao_campo.md`; guardar relatório com precisão, recall, F1, matriz de confusão e rejeição por classe.
- Se a sugestão estiver fraca, corrigir **um bug demonstrado** (ex.: EXIF, cor, contrato de RGB, carregamento incorreto de artefato) e refazer regressão.
- Se não houver dados revisados suficientes para novo treinamento + validação realmente separada, **não re-treinar o modelo na véspera**. Manter sugestão assistida, pedir confirmação e explicar limitações.
- **Proibição de falseamento:** não selecionar apenas fotos que acertam, não apresentar acerto da regra após confirmação como acurácia do reconhecedor e não ajustar limiar apenas para produzir um número maior em teste.

## 4. Agenda de quatro dias

| Data | Trabalho de maior impacto | Conclusão esperada |
| --- | --- | --- |
| **07/11 — Dia 1** | Congelar requisitos do manual; instalar em ambiente limpo; rodar CI/local; iniciar coleta de fotos novas, inventariar erros de reconhecimento e selecionar experiências reais de filtro/segmentação | T01–T04/T12 iniciais; conjunto de teste identificado |
| **08/11 — Dia 2** | Executar avaliação com o modelo atual; agrupar erros por classe/cenário; consertar bugs de alta frequência; comprovar operações PDI com duas fotos reais e casos difíceis | T05–T10 com relatórios/figuras reais, diagnóstico de erros |
| **09/11 — Dia 3** | Congelar o programa candidato; testar PC/Android/iPhone; revisar login, acesso e recuperação de erro; completar resultados, proposta e desenvolvimento no relatório | T11/T13 e documentação técnica revisados |
| **10/11 — Dia 4** | Fazer três ensaios cronometrados de 10–15 min, corrigir apenas defeitos bloqueadores, repetir CI e smoke do SHA definitivo, registrar release/tag e finalizar/postar o trabalho | T14/T15, evidências vinculadas ao mesmo SHA |
| **11/11 — Entrega** | Verificar comprovante, acesso ao programa e cópia offline no dispositivo; apresentar a versão já congelada | Sem alterações de última hora |

Se houver atualização do código após o ensaio do dia 10, repetir os testes atingidos e fixar novo SHA; não reaproveitar o aceite do commit antigo.

## 5. Preparação da demonstração executável

O projeto atual é **Streamlit/Python**, não um executável Windows independente. O manual recuperado solicita um programa que implemente a proposta; não é justificável gastar a janela final com `PyInstaller` sem exigência explícita da professora.

### Comandos de referência

```bash
python --version
python -m pip install -e '.[dev]'
python -m ruff check src scripts tests
python -m pytest -q
python -m pip check
python scripts/run_processing_lab.py --output reports/processing_lab
streamlit run streamlit_app.py
```

Para validação de governança e requisitos operacionais, há também:

```bash
python scripts/run_acceptance_checks.py --diagnostic
```

**Não apresentar esse último comando como se aprovasse a entrega final.** Preparar o ambiente na própria máquina em que será demonstrado, verificar o modelo ONNX e todas as dependências **antes do seminário** e ter imagens de teste autorizadas como plano de contingência. Uma instalação sem rede só é garantida se o ambiente e os pacotes já estiverem presentes; validar isso de verdade.

## 6. Ordem de corte se faltar tempo

1. **Nunca cortar:** app abre, imagens processam, filtros e segmentação são demonstráveis, descarte confirmado funciona, erros são tratados, documentação e entrega APS.
2. **Simplificar conscientemente:** limitar apresentação da classificação automática às três classes prioritárias, mantendo encaminhamento manual correto para as demais.
3. **Postergar:** treino profundo, automação sem confirmação, novos módulos sociais, performance não medida, backup institucional completo, migração do encoder, transformar Streamlit em `.exe` sem exigência explícita.
4. **Não ocultar:** reconhecimentos errados, dataset pequeno, limitações de fundo/iluminação, módulos fora do escopo, teste público não reexecutado e falhas remanescentes.

## 7. Decisão GO/NO-GO acadêmica

**GO** quando T01–T15 aplicáveis estiverem demonstrados com evidência, não houver bloqueador de abertura/segurança, o relatório estiver coerente com o código e o professor puder executar a solução proposta. A taxa do modelo é **relatada, não inventada**; falhas podem ser discutidas se o fluxo principal mantém comportamento seguro e útil.

**NO-GO** se o programa não inicia em ambiente da demonstração, upload/filtragem/segmentação não funcionam, o documento omite itens obrigatórios do manual, há erro de isolamento de dados ou o sistema fornece descarte definitivo apenas com classificação possivelmente incorreta.

**Relação com o plano geral:** [roadmap_entrega.md](roadmap_entrega.md), [roteiro_testes_manuais.md](roteiro_testes_manuais.md), [pratica_processamento_imagens.md](pratica_processamento_imagens.md), [avaliacao_campo.md](avaliacao_campo.md).
