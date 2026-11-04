# Roadmap de entrega

## 1. Candidato de release

- manter `main` verde com testes, lint, `pip check` e diagnóstico;
- revisar Secrets e executar as migrações no projeto Supabase correto;
- testar o URL público em Android, iOS e computador — concluído em 04/11/2026 para a jornada de visitante;
- registrar hash, data, responsável e resultado do smoke test — código funcional `16344df`, CI verde e evidência no [roteiro de aceite](roteiro_testes_manuais.md);
- corrigir qualquer falha de abertura, sessão ou upload.

**Aceite:** visitante abre o app, envia foto e consulta orientação; participante entra e acompanha protocolo; gestão acessa apenas com autorização.

## 2. Validação do reconhecimento

- coletar um conjunto novo com foco em garrafa PET, lata e embalagem de vidro;
- separar por objeto e cena para impedir vazamento;
- congelar hashes antes de avaliar;
- medir precisão, recall, F1, rejeição e matriz de confusão por classe;
- documentar fotos difíceis, falhas e limiares.

**Aceite:** relatório reproduzível e independente, sem uso do conjunto para ajustar o mesmo candidato.

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

- dividir `ui/streamlit_app.py` por página;
- adicionar testes de contrato entre páginas e serviços;
- decidir e publicar a licença do código;
- criar tag, changelog e notas da primeira release candidata.

**Aceite:** revisão de código simples, documentação alinhada e release rastreável.
