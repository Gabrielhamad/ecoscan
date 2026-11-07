# Parecer de prontidão de entrega — EcoScan

**Data-base:** 07/11/2026  
**Commit auditado:** `04c1a34bcb22026e03b2a3b2396856c2994746e1` (`main`)  
**Escopo da revisão:** estrutura do repositório, arquitetura, engenharia do código, documentação, CI, governança e requisitos de entrega.  
**Método:** revisão estática de arquivos e registros versionados, metadados e resultados do GitHub Actions. **Não equivale a auditoria linha a linha, teste de invasão, ensaio de recuperação nem aceite manual no deploy atual.**

## Decisão executiva

| Destino da entrega | Decisão | Justificativa |
| --- | --- | --- |
| Demonstração acadêmica do software | **Candidato tecnicamente apto** | Estrutura modular, funções demonstráveis e qualidade automatizada verde; requer fechar identificação autoral, evidências e aceite da versão publicada |
| Entrega acadêmica formal e rastreável | **Liberação condicionada (GO após P0)** | Ainda faltam aceite no SHA definitivo, pacote de APS validado e release/manifesto de entrega |
| Piloto orientativo supervisionado | **Condicionado ao aceite operacional do deploy** | Reconhecimento assistido e confirmação humana preservados; serviços persistentes exigem revisão de continuidade |
| Operação institucional sem acompanhamento | **NO-GO** | Falta ensaio de restauração/indisponibilidade, observabilidade e avaliação de campo independente; ausência de métricas contratuais de operação |

O modelo não precisa atingir acurácia perfeita para a **entrega de Engenharia de Software**. É obrigatório, porém, que a interface e o relatório apresentem com precisão o reconhecimento **assistido**, sem atribuir certeza às sugestões visuais ou afirmar validação independente inexistente.

## Evidências positivas verificadas

| Eixo | Evidência concreta | Parecer |
| --- | --- | --- |
| Estrutura de código | `src/ecoscan/` separado em `ui`, `services`, `classification`, `image_processing`, `segmentation`, `disposal`, `training`; entry point específico Streamlit | Boa divisão por responsabilidade, adequada ao escopo |
| Refatoração | `ui/streamlit_app.py` possui ~488 linhas; navegação, sessão tipada e controladores de análise/páginas em módulos próprios | Melhor manutenção e redução de acoplamento; não prova ausência de todo débito técnico |
| Qualidade automatizada | [GitHub Actions — Qualidade, run 42061103008](https://github.com/Gabrielhamad/ecoscan/actions/runs/42061103008), mesmo SHA da revisão: **496 testes, 108 subtestes, 7 avisos**; Ruff, `pip check` e PostgreSQL aprovados | Gate de CI aprovado |
| Banco e autorização | Migrações `001`–`004` e testes de privilégios em PostgreSQL 16 na CI; aceite integrado do Supabase documentado em 04/11/2026 | Evidência sólida de implementação e teste; não substitui teste de restauração |
| Documentação | `README.md`, arquitetura, modelo, gestão da base, controles de acesso, plano de testes, hospedagem e recuperação | Boa cobertura funcional e técnica |
| Colaboração | `CONTRIBUTING.md`, `SECURITY.md`, `CODEOWNERS`, template de PR e issue de bug, Dependabot | Base de governança existente |
| Modelo e resultados | `docs/modelo_reconhecimento.md` e relatórios versionados reproduzem avaliação histórica e diagnóstico TrashNet; o fluxo exige confirmação da classe | Declaração honesta do estágio técnico |
| Reprodutibilidade | Python 3.12, `pyproject.toml`, `requirements.txt`, workflow CI, `Dockerfile` e scripts operacionais | Boa base; versões amplas ainda limitam repetibilidade plena |

**Atenção à leitura da CI:** o workflow agendado `Treinamento revisado` aparece diversas vezes no histórico. Sucesso nesse workflow **não comprova** novo modelo treinado, precisão superior ou aprovação do sistema. Para qualidade de código, usar o workflow específico `Qualidade do EcoScan`.

## Riscos e lacunas efetivamente observados

| ID | Achado | Impacto e classificação | Referência / ação |
| --- | --- | --- | --- |
| A01 | A `main` está sem proteção de branch (`protected: false`) | **P1 — Governança:** merges e políticas de revisão não são compulsórios | [Issue #15](https://github.com/Gabrielhamad/ecoscan/issues/15) |
| A02 | Não há GitHub Release publicado nem licença de software definida na raiz (`license: null`) | **P0 release / P1 licença:** rastreabilidade e reutilização formal pendentes | [Issues #11](https://github.com/Gabrielhamad/ecoscan/issues/11) e [#15](https://github.com/Gabrielhamad/ecoscan/issues/15) |
| A03 | O aceite público em PC, Android e iPhone documentado corresponde ao commit anterior `16344df`, não a `04c1a34` | **P0 — Qualidade de entrega:** o deploy atual ainda não tem aceite de aparelhos anexado | [Issue #10](https://github.com/Gabrielhamad/ecoscan/issues/10) |
| A04 | Não há evidência de restauração real isolada do Supabase Auth, banco e Storage, nem RPO/RTO acordados | **P1 — Bloqueador institucional:** continuidade operacional não demonstrada | [Issue #13](https://github.com/Gabrielhamad/ecoscan/issues/13) |
| A05 | Não há avaliação independente, congelada, com fotos novas reais de celular que comprove desempenho no campo | **P1 — Limite de escopo do modelo:** manter classificação assistida | [Issue #14](https://github.com/Gabrielhamad/ecoscan/issues/14) |
| A06 | A autoria acadêmica continua com placeholders de nomes e RAs | **P0 — Pacote acadêmico:** requisitos institucionais precisam ser preenchidos com dados reais no documento final | [Issue #12](https://github.com/Gabrielhamad/ecoscan/issues/12) |
| A07 | Dependências com faixas amplas; grande encoder armazenado no Git; repositório com ~169 MB registrados em metadados do GitHub | **P2 — Evolução:** builds menos determinísticos e clones maiores | [Issue #16](https://github.com/Gabrielhamad/ecoscan/issues/16) |
| A08 | Observabilidade persistente e runbook de incidente ainda não aprovados em ambiente real | **P2 — Evolução; importante no uso institucional** | [Issue #17](https://github.com/Gabrielhamad/ecoscan/issues/17) |
| A09 | Quatro PRs de atualização do Dependabot estão abertos | **P2 — Manutenção:** revisar compatibilidade e CI antes de aceitar; não são bugs confirmados | [Pull requests](https://github.com/Gabrielhamad/ecoscan/pulls) |
| A10 | Sete avisos `Pandas4Warning` originados na integração Streamlit/Pandas | **P2 — Compatibilidade futura:** não causaram reprovação na CI | [Execução da qualidade](https://github.com/Gabrielhamad/ecoscan/actions/runs/42061103008) |

Não foi verificada a existência de uma política obrigatória de aprovação de PR, pois `protected: false` no branch auditado. A existência de `CODEOWNERS` e de um template de PR não equivale à aplicação de regras de aprovação pelo GitHub.

## Limite do reconhecimento e do aceite

A avaliação histórica do classificador registrou 101/145 primeiras escolhas corretas; o diagnóstico TrashNet para metal/plástico/vidro registrou 186/224. Esses números pertencem aos conjuntos avaliados, com ressalvas de proveniência e de cenário, e **não são métricas de produção**. A confirmação manual do material antes de liberar instruções completas deve ser mantida.

O aplicativo público está anunciado em `https://ecoscan-gabrielhamad.streamlit.app`, mas a inspeção desta revisão não executou o percurso funcional completo no navegador público. Não registrar a aplicação como 'aprovada no SHA atual' sem executar o [roteiro de testes](roteiro_testes_manuais.md).

## Critério para liberar cada uso

### Gate A — Entrega acadêmica

- [x] Código modular e revisão do repositório auditados.
- [x] CI do SHA de referência aprovada com testes, lint e banco.
- [x] Documentação de arquitetura, modelo e operação disponível.
- [ ] [A01 acadêmico] Aceite de computador, Android, iPhone, contas e gestão no **SHA final publicado** — issue #10.
- [ ] [A02 acadêmico] Versão/tag e manifesto de entrega com evidências de CI e retorno — issue #11.
- [ ] [A03 acadêmico] Identificação dos autores, adequação ao manual e pacote da APS aprovados — issue #12.

**Decisão atual:** **NO-GO formal**, mas o produto é **candidato técnico à entrega**. Não fazer mais refatorações extensas sem defeito demonstrado; encerrar os três itens acima.

### Gate B — Piloto controlado

Exige o Gate A, escopo assistido declarado, autorização e revisão dos fluxos persistentes publicados, rotina de atendimento/erro e responsável operativo. Não pressupõe precisão automática por classe.

### Gate C — Operação institucional

Exige os Gates A/B e demonstração em ambiente autorizado de restauração completa, indisponibilidade, controle de acesso persistente e critérios de segurança e desempenho pactuados. O reconhecimento automatizado é um **gate independente**: só avançar mediante validação de campo e aprovação por classe.

## Nota sobre autoria e escopo desta auditoria

Nenhum integrante ou aprovador foi inventado; os papéis devem ser atribuídos pelo grupo. Este parecer verifica **conformidade estrutural observável** e evidências disponíveis no GitHub, não certifica segurança absoluta, cobertura total dos requisitos da instituição ou aceitação do produto pela banca.

**Próximos documentos:** [Roadmap de entrega](roadmap_entrega.md) · [Plano de gestão](gestao_projeto.md) · [Arquitetura da interface](arquitetura_interface.md).
