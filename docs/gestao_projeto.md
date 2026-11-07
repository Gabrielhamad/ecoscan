# Plano de gestão do projeto — EcoScan

**Versão de referência:** 07/11/2026 · `main` `04c1a34`.  
**Natureza:** projeto acadêmico de Engenharia de Software com protótipo funcional de educação ambiental.  
**Status do ciclo:** preparação de release candidata; não assumir operação institucional aprovada.

## 1. Termo de abertura e objetivo

**Problema:** orientar a identificação visual assistida de resíduos, seu descarte e a participação ambiental, oferecendo também controles para revisão e gestão de informações do projeto.

**Objetivo da fase atual:** entregar um protótipo demonstrável e tecnicamente rastreável, com documentação da arquitetura, qualidade automatizada, evidências dos requisitos, procedimento de instalação e demonstração funcional.

**Resultado aceito:** pacote acadêmico revisado, versão de código e modelo identificáveis, demonstração aprovada no mesmo SHA publicado e limitações técnicas registradas.

**Fora do escopo desta entrega:** afirmar reconhecimento automático infalível; atender como canal oficial municipal; uso institucional sem critérios de continuidade e autorização; afirmar treino do modelo por mero sucesso de workflow agendado.

## 2. Escopo e entregáveis controlados

| ID | Entregável | Local de evidência | Gate |
| --- | --- | --- | --- |
| E01 | Código funcional, arquitetura modular e configuração documentada | `src/ecoscan/`, `config/`, `docs/arquitetura_interface.md` | A |
| E02 | Reconhecedor ONNX com confirmação humana e regras ambientais | `models/`, `docs/modelo_reconhecimento.md`, `disposal/` | A |
| E03 | Testes de software, permissões do banco e análise estática | `tests/`, `.github/workflows/quality.yml`, CI do SHA | A |
| E04 | Manual de instalação e roteiro de demonstração | `README.md`, `docs/roteiro_testes_manuais.md` | A |
| E05 | Relatório final e referências da APS | Artefato acadêmico externo aprovado e registro resumido | A |
| E06 | Tag/release, changelog e manifesto de evidências | GitHub Releases, `CHANGELOG.md`, registro de aceite | A |
| E07 | Recuperação comprovada da persistência em ambiente isolado | `docs/recuperacao_operacional.md` + relatório privado | C |
| E08 | Avaliação de campo independente | `docs/avaliacao_campo.md` + relatório anonimizado | Gate do modelo |

Os artefatos com nomes completos/RAs, dados de conta, backups, fotos privadas e credenciais devem permanecer no local apropriado de acesso restrito; o GitHub público pode conter somente referências e evidências anonimizadas.

## 3. Papéis, responsáveis e matriz RACI

**Não há responsáveis reais atribuídos nesta versão.** O grupo deve preencher uma pessoa por papel, podendo uma pessoa acumular mais de um papel. O registro de autoria civil fica no trabalho final, não em uma issue pública.

| Atividade | Coordenação da APS | Desenvolvimento | QA/Testes | Infra/Operação | Revisor |
| --- | --- | --- | --- | --- | --- |
| Escopo, cronograma e aceite acadêmico | A | C | C | I | C |
| Implementação/refatoração | I | R/A | C | C | C |
| Verificação CI e teste em aparelhos | A | C | R | C | C |
| Relatório, autores, referências ABNT | R/A | C | C | I | C |
| Banco, backup, segredos, implantação | I | C | C | R/A | C |
| Release e retorno controlado | A | R | C | R | C |
| Decisão de liberação final | A | C | C | C | R |

**Legenda:** R = executa; A = aprova e responde pela decisão; C = consultado; I = informado. A designação nominal e a aprovação por segunda pessoa são **pendentes**, não presumidas.

## 4. Fluxo de trabalho e controle de mudança

**Fonte da verdade:** GitHub Issues para tarefas/bugs e critérios de aceite; Pull Requests para alterações; GitHub Actions para CI; documentos `docs/` para decisões/evidências; GitHub Releases para versões estáveis.

**Kanban sugerido:** Backlog → Pronto → Em execução → Em revisão → Aceite → Concluído. O estado deve ser atualizado pela equipe; este documento não configura automaticamente um quadro GitHub Projects.

**Regras operacionais:**

1. Abrir issue com problema, impacto, prioridade, critério de aceite, evidência desejada e papel responsável.
2. Escolher uma issue pronta; criar branch `feat/`, `fix/`, `docs/` ou `refactor/` vinculada ao número.
3. Manter mudanças focadas e testes de regressão proporcionais ao risco; atualizar documentação na mesma alteração.
4. Abrir PR com referência à issue, resumo, teste realizado, risco, rollback e impacto em usuário/banco/modelo.
5. Exigir CI verde; revisão independente quando houver equipe e proteção de branch habilitada.
6. Após merge, repetir smoke conforme impacto, atualizar issue e changelog; somente depois considerar uma release.
7. Para mudanças em modelo/migração, exigir comparação de hashes, proveniência, compatibilidade e plano de reversão específico.

**Política proposta de priorização:**
- **P0:** impede evidência essencial da entrega acadêmica ou expõe erro crítico de acesso/segurança.
- **P1:** necessário para qualidade de piloto/produção, governança robusta ou melhora de validade de afirmações do produto.
- **P2:** redução de dívida técnica ou otimização sem impacto imediato na entrega demonstrável.

## 5. Definition of Ready (DoR) e Definition of Done (DoD)

Uma issue está **pronta** quando tem: problema reproduzível ou objetivo mensurável, escopo, entradas e saídas, dependências, prioridade e critério de aceite verificável.

Uma alteração está **concluída** quando tem:
- implementação revisável e sem segredo/dado pessoal versionado;
- testes relevantes adicionados/atualizados, Ruff e CI verdes;
- evidências e documentação coerentes com o novo comportamento;
- tratamento dos riscos de segurança, esquema e compatibilidade;
- aprovação do PR e resultado do aceite aplicável;
- link do SHA/PR, registro do responsável e issue encerrada.

**Importante:** DoD de uma alteração não equivale a Gate A/C do projeto. Sem smoke no aplicativo publicado, não registrar "operação validada", ainda que a CI esteja verde.

## 6. Comunicação, mudanças e riscos

A equipe deve realizar checkpoint por marco e registrar em comentário de issue ou ata versionada sem dados privados:
**último SHA aprovado; entregas concluídas; bloqueios; riscos novos; decisões; responsável pela próxima ação; evidência esperada.** Não há cadência ou prazo assumidos enquanto o grupo não os definir.

| Risco | Probabilidade / impacto qualitativos | Contenção e referência |
| --- | --- | --- |
| R1 — divergência entre commit testado e deploy publicado | Incerto / alto | Fixar SHA, confirmar versão no URL e executar issue [#10](https://github.com/Gabrielhamad/ecoscan/issues/10) |
| R2 — erro de permissão ou perda de dados no ambiente real | Incerto / muito alto | Não usar dados reais no ensaio; revisar RLS e restaurar em ambiente isolado, issue [#13](https://github.com/Gabrielhamad/ecoscan/issues/13) |
| R3 — atribuição de precisão do reconhecedor acima da evidência | Conhecido / alto | Exibir classificação assistida; avaliar novo conjunto independente, issue [#14](https://github.com/Gabrielhamad/ecoscan/issues/14) |
| R4 — alteração direta não revisada em `main` | Possível / moderado-alto | Regras de branch, revisão e CODEOWNERS, issue [#15](https://github.com/Gabrielhamad/ecoscan/issues/15) |
| R5 — build não reproduzível ou encoder pesado | Possível / moderado | Constraints, cold start e artefato versionado, issue [#16](https://github.com/Gabrielhamad/ecoscan/issues/16) |
| R6 — falha difícil de diagnosticar após deploy | Possível / moderado-alto | Telemetria sem dado pessoal e runbook, issue [#17](https://github.com/Gabrielhamad/ecoscan/issues/17) |
| R7 — identificação autoral e referências incompletas | Conhecido / alto para a APS | Conferência do manual, nomes/RAs reais no arquivo final, issue [#12](https://github.com/Gabrielhamad/ecoscan/issues/12) |

Probabilidades não foram quantificadas sem base; o responsável deverá reavaliar riscos e registrar decisão de aceitar, mitigar, transferir ou evitar cada um.

## 7. Indicadores e acompanhamento

| Indicador | Como medir | Critério de acompanhamento |
| --- | --- | --- |
| Saúde da branch candidata | CI de qualidade por SHA | Dois jobs de qualidade e PostgreSQL aprovados; sem bypass do gate |
| Progresso da entrega | Issues P0 aceitas / P0 totais | 100% antes do Gate A |
| Cobertura de cenários críticos | Matriz de teste em ambiente publicado | Nenhum cenário essencial sem resultado e evidência |
| Rastreabilidade | Issues ligadas a PR/SHA e evidência | Cada alteração entregável rastreável |
| Retorno de mudanças | Procedimento e ensaio no ambiente permitido | Resultado documentado, não somente plano textual |
| Qualidade do modelo | Precisão, recall, F1 e taxa de rejeição por classe | Métricas reportadas por origem; não usar benchmark histórico como produção |

**Sem meta de performance falsa:** tempos e taxas do ambiente real só devem ser registrados após medição. A disciplina de gestão é manter metas explícitas e medir, não inventar números.

## 8. Encerramento da fase

O coordenador reúne: versão congelada, ci verde, aceite em aparelhos reais, autores e documentação final, checklist de requisitos, lista de pendências aceitas e decisão registrada (GO/NO-GO). Depois de aprovado, os itens P1/P2 podem seguir em ciclos posteriores sem comprometer a demonstração acadêmica, **desde que** não haja defeito crítico de segurança ou perda de dados.

Consulte [Roadmap](roadmap_entrega.md), [Parecer de prontidão](parecer_prontidao_2026-11-07.md) e [Contribuição](../CONTRIBUTING.md).
