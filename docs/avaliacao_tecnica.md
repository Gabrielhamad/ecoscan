# Avaliação técnica para entrega

## Resultado da revisão

O projeto tem um fluxo funcional amplo e boa cobertura automatizada. A revisão consolidou o reconhecimento em uma única implementação, retirou fallbacks e artefatos históricos do runtime, reduziu dependências e alinhou configuração, interface e documentação.

O estado atual é adequado para **piloto controlado**. Ainda não é adequado para declarar reconhecimento automático ou operação institucional sem acompanhamento.

## Bloqueios

| Prioridade | Ponto | Evidência | Ajuste necessário |
| --- | --- | --- | --- |
| P0 | Aceite no ambiente publicado | Jornada de visitante aprovada em computador, Android e iPhone no código `16344df` | Repetir após mudanças de runtime e concluir contas, gestão e Supabase |
| P0 | Banco e autorização reais | A CI valida migrações em PostgreSQL local, sem Secrets de produção | Validar cadastro, confirmação, login, perfil de gestão, Storage privado e RLS no Supabase usado pelo app |
| P0 | Reconhecimento independente | A release tem resultado histórico, com confirmação obrigatória | Coletar e congelar teste novo para metal, plástico e vidro; publicar métricas e erros por classe |
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

## Critério de pronto para entrega

A entrega pode ser marcada como candidata quando todos os P0 tiverem evidência anexada, a CI do hash estiver verde e o mesmo hash tiver sido testado no URL público. Reconhecimento automático deve continuar desativado até o gate independente por classe.
