# Roadmap de entrega

## 1. Candidato de release

- manter `main` verde com testes, lint, `pip check` e diagnóstico;
- revisar Secrets e executar as migrações no projeto Supabase correto;
- aplicar a migration 004, auditar identidades antigas e validar as constraints;
- testar o URL público em Android, iOS e computador — concluído em 04/11/2026 para a jornada de visitante;
- registrar hash, data, responsável e resultado do smoke test — código funcional `16344df`, CI verde e evidência no [roteiro de aceite](roteiro_testes_manuais.md);
- corrigir qualquer falha de abertura, sessão ou upload.

**Aceite:** visitante abre o app, envia foto e consulta orientação; participante entra e acompanha protocolo; gestão acessa apenas com autorização.

**Estado:** smoke público de visitante concluído; fronteira de autorização e CI
do banco reforçadas; cadastro, duas contas, isolamento, revisão por analista e
resposta ao autor concluídos em 04/11/2026 no código funcional `0ad6ed7`. Ainda
no mesmo dia, a migration 004 e suas constraints foram validadas, os buckets
foram confirmados privados e passaram revogação de analista, relatos, pontos e
testes de campo. Falta o ensaio de continuidade operacional.

## 2. Validação do reconhecimento

- coletar um conjunto novo com foco em garrafa PET, lata e embalagem de vidro;
- separar por objeto e cena para impedir vazamento;
- congelar hashes antes de avaliar;
- medir precisão, recall, F1, rejeição e matriz de confusão por classe;
- documentar fotos difíceis, falhas e limiares.

**Aceite:** relatório reproduzível e independente, sem uso do conjunto para ajustar o mesmo candidato.

**Estado:** avaliação histórica reproduzida por hash e diagnóstico externo
TrashNet concluído com 224 imagens prioritárias. O teste novo de celular por
objeto e sessão continua pendente e não pode ser substituído por esse benchmark.

## 3. Operação e observabilidade

- persistir eventos técnicos sem imagens ou dados pessoais;
- monitorar erro, latência, versão e indisponibilidade do banco;
- testar backup e restauração;
- ensaiar rollback de código e release do modelo.

**Aceite:** incidente simulado recuperado sem perder protocolos confirmados.

## 4. Redução do repositório

- hospedar encoder versionado em storage confiável;
- baixar por checksum com cache e timeout;
- validar cold start antes de remover as partes do Git;
- produzir imagem Docker reproduzível ou constraints de dependências.

**Aceite:** clone e build menores, com funcionamento offline/degradado claramente definido.

## 5. Manutenção estrutural

- **concluído em #7:** extrair oito módulos de interface para processamento, descarte, campanhas, relatos, administração, sistema, utilitários e operações de upload; o coordenador passou a 906 linhas;
- **concluído em #7:** acrescentar testes de reexportação, dependências acíclicas e limite de tamanho do coordenador;
- **próxima etapa:** extrair controladores de navegação e sessão tipados, com validação end-to-end para novos estados de página;
- decidir e publicar a licença do código;
- criar tag, changelog e notas da primeira release candidata.

**Aceite:** revisão de código simples, documentação alinhada e release rastreável.
