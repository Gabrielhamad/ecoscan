# Documentação atual

[Voltar ao README](../README.md)

Esta pasta descreve o produto presente no `main`. Resultados e métodos substituídos permanecem acessíveis pelo histórico do Git.

## Produto e engenharia

| Documento | Finalidade |
| --- | --- |
| [Arquitetura atual](arquitetura_atual.md) | Componentes, fronteiras e fluxo de execução |
| [Arquitetura modular da interface](arquitetura_interface.md) | Camadas, dependências e extensão segura das páginas Streamlit |
| [Autoria acadêmica](autoria_aps.md) | Registro correto dos integrantes e suas contribuições |
| [Modelo de reconhecimento](modelo_reconhecimento.md) | Release ONNX, segurança, métricas e atualização |
| [Avaliação técnica](avaliacao_tecnica.md) | Riscos, bloqueios e qualidade observada |
| [Roadmap de entrega](roadmap_entrega.md) | Marcos, backlog, priorização, rastreabilidade e gates de liberação |
| [Validação da APS em quatro dias](plano_validacao_aps_4_dias.md) | Matriz de testes técnicos, evidências PDI, avaliação honesta do modelo e roteiro até 11/11 |
| [Parecer de prontidão — 07/11/2026](parecer_prontidao_2026-11-07.md) | Diagnóstico fundamentado do GitHub e decisão de entrega por cenário |
| [Gestão do projeto](gestao_projeto.md) | Termo de abertura, entregáveis, papéis, RACI, riscos, mudança, DoR e DoD |
| [Escopo e variações](escopo_e_variacoes.md) | Materiais, objetos e casos fora do escopo |
| [Processamento preservado](processamento_preservado_v2.md) | Contrato RGB usado no treino e na inferência |
| [Prática de processamento](pratica_processamento_imagens.md) | Filtros, segmentação e morfologia |

## Operação

| Documento | Finalidade |
| --- | --- |
| [Guia do grupo](guia_do_grupo.md) | Teste por participantes |
| [Operação da secretaria](operacao_secretaria.md) | Revisão, campanhas e protocolos |
| [Autenticação](autenticacao.md) | Contas, perfis e autorização |
| [Banco](banco_gratuito.md) | Supabase, migrações e armazenamento |
| [Campanhas e relatos](campanhas_e_relatos.md) | Persistência compartilhada e retorno |
| [Recuperação operacional](recuperacao_operacional.md) | Backup, rollback e incidentes |
| [Hospedagem](hospedagem_gratuita.md) | Publicação no Streamlit Cloud |

## Dados e reconhecimento

| Documento | Finalidade |
| --- | --- |
| [Gestão do dataset](gestao_dataset_e_classes.md) | Entrada, curadoria, split e proveniência |
| [Captura de imagens públicas](captura_web_dataset.md) | Fontes, direitos e deduplicação |
| [Anotações de objetos](anotacoes_objetos.md) | Caixas revisadas e exportação COCO |
| [Treino com contribuições](treino_contribuicoes.md) | Fila privada, gates e publicação |
| [Roteiro de testes](roteiro_testes_manuais.md) | Aceite manual em celular e computador |
| [Avaliação com fotos reais](avaliacao_campo.md) | Protocolo de coleta, auditoria de grupos e métricas por classe |

## Critério de leitura

Código, configuração ativa e teste automatizado têm precedência sobre texto antigo. Uma funcionalidade implementada ainda precisa de aceite no ambiente publicado para ser declarada operacional.
