# Avaliação técnica para entrega

## Resultado da revisão

O projeto tem um fluxo funcional amplo e boa cobertura automatizada. A revisão consolidou o reconhecimento em uma única implementação, retirou fallbacks e artefatos históricos do runtime, reduziu dependências e alinhou configuração, interface e documentação.

O estado atual é adequado para **piloto controlado**. Ainda não é adequado para declarar reconhecimento automático ou operação institucional sem acompanhamento.

## Bloqueios

| Prioridade | Ponto | Evidência | Ajuste necessário |
| --- | --- | --- | --- |
| P0 | Aceite no ambiente publicado | Visitante aprovado em computador, Android e iPhone; contas e gestão aprovadas no código `0ad6ed7` | Repetir o smoke após mudanças de runtime |
| P0 | Continuidade do banco | Migration 004, constraints, buckets privados, revogação, contribuições, relatos, pontos e testes passaram no Supabase publicado | Ensaiar exportação/restauração e indisponibilidade em janela controlada |
| P0 | Reconhecimento independente | A avaliação histórica agora é reproduzível por hash: 101/145 top-1 e 47/51 aceitos corretos, mas reutiliza vetores de desenvolvimento | Coletar e congelar teste novo por objeto/sessão para metal, plástico e vidro; publicar métricas, rejeição e erros por classe |
| P0 | Rollback operacional | Código tem histórico, mas não há release Git versionada | Criar tag de entrega, changelog e procedimento testado de retorno do app e do modelo |

## Riscos altos

| Ponto | Impacto | Ajuste recomendado |
| --- | --- | --- |
| Encoder no Git | O repositório contém cerca de 168 MB só no encoder e aumenta clone/build | Publicar o artefato em storage versionado com checksum e cache; manter no Git apenas metadados e licença após validar o download |
| Interface monolítica | `ui/streamlit_app.py` ainda possui cerca de 3 mil linhas | Separar páginas públicas, conta, gestão e sistema em módulos, mantendo `main()` como orquestrador |
| Observabilidade | Logs locais não sobrevivem necessariamente ao Streamlit Cloud | Registrar latência, erro, revisão e versão sem foto nem dado pessoal em backend persistente |
| Dependências sem lock | Faixas amplas podem resolver versões diferentes em novos builds | Gerar lock/constraints para deploy e automatizar atualização controlada |

## Riscos médios

- Não há licença do código do projeto na raiz. A licença do encoder está presente, mas não define o uso do software EcoScan.
- Não há tag de release no Git; o estado de entrega depende do hash do `main`.
- A documentação técnica ainda possui material acadêmico histórico fora do índice atual. O histórico útil deve ficar no Git ou em pacote de evidências, sem orientar a operação.
- A câmera ao vivo depende de servidor separado; no Streamlit Cloud, o fluxo suportado é captura estática ou upload.
- Há avisos de compatibilidade futura do Streamlit com Pandas em testes de gráficos; pertencem à dependência, mas devem ser acompanhados.

## Qualidade verificada nesta revisão

- seleção de modelo sem fallback implícito;
- hashes e contrato de preparação preservados;
- dependências antigas de treino removidas do deploy;
- abertura pública sem carregar NumPy, Pillow e serviços administrativos;
- suíte automatizada, lint crítico e `pip check` executados;
- migrações e workflow de qualidade presentes no repositório.
- diagnóstico somente leitura para tabelas e buckets do Supabase;
- autorização explícita na fila remota de correções e constraints para novas identidades persistentes.

## Critério de pronto para entrega

A entrega pode ser marcada como candidata quando todos os P0 tiverem evidência anexada, a CI do hash estiver verde e o mesmo hash tiver sido testado no URL público. Reconhecimento automático deve continuar desativado até o gate independente por classe.
