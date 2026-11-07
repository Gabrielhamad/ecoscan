# Validação de aceite - EcoScan

Gerado em UTC: `2026-11-07T20:49:15+00:00`.
Versão: `0.1.0`; commit: `89622ec714b815c216a9215ab9ba69999b39c6b8`.
O commit não atesta ausência de alterações locais. Verificar o diff antes de publicar.
Inspeção estática e smoke test não equivalem a aceite real ou acurácia.

## Resumo

- OK: 9.
- Atenção: 4.
- Pendente: 8.
- Falha: 0.

## Checks

| Código | Área | Status | Tipo | Evidência | Detalhes |
|---|---|---:|---|---|---|
| QA-01 | Estrutura | ok | static | `src/ecoscan/ui/streamlit_app.py, src/ecoscan/app/pipeline.py, src/ecoscan/image_processing/filters.py, src/ecoscan/segmentation/adaptive.py, src/ecoscan/segmentation/methods.py, src/ecoscan/classification/runtime.py, src/ecoscan/live_camera/server.py, src/ecoscan/disposal/collection_points.py, src/ecoscan/disposal/impact.py, src/ecoscan/services/photo_requirements.py, src/ecoscan/services/accounts.py, src/ecoscan/services/campaigns.py, src/ecoscan/services/civic_reports.py, src/ecoscan/services/operations.py, src/ecoscan/services/final_readiness.py, src/ecoscan/services/recognition_safety.py, src/ecoscan/services/usage_quality.py, src/ecoscan/services/public_flow.py, src/ecoscan/services/recognition_improvement.py, src/ecoscan/services/model_governance.py, src/ecoscan/services/deployment_readiness.py, src/ecoscan/services/access_plan.py, src/ecoscan/services/field_testing.py, streamlit_app.py, scripts/generate_final_readiness.py, scripts/check_deployment_ready.py, docs/hospedagem_gratuita.md, docs/roadmap_entrega.md, config/user_profiles.json, config/campaigns.json, tests` | Estrutura principal encontrada. |
| QA-02 | Orientações | ok | automated | `config/disposal_guidance.json` | Todas as classes têm orientação. |
| QA-12 | Destinos | ok | automated | `config/disposal_targets.json; assets/disposal_targets` | Classes ativas possuem cor, imagem de referência, preparo e busca no mapa. |
| QA-13 | Impacto ambiental | ok | automated | `config/environmental_impacts.json` | Classes ativas possuem riscos do mau descarte, ação positiva e fonte de referência. |
| QA-14 | Plano de fotos | ok | automated | `config/photo_requirements.json` | Classes ativas possuem exemplos, variações, restrições e meta mínima de imagens. |
| QA-15 | Pontos de coleta | attention | automated | `config/collection_points.json; src/ecoscan/disposal/collection_points.py` | 22 ponto(s) cadastrados; classes cobertas: glass, metal, paper_cardboard, plastic. |
| QA-03 | Validação | ok | automated | `src/ecoscan/image_processing/validation.py` | Arquivo vazio foi rejeitado corretamente. |
| QA-04 | Modelo | ok | automated | `/workspace/work/ecoscan/models/semantic-v1/semantic.json` | Modelo selecionado: semantic_onnx_assisted. |
| QA-05 | Inferência | pending | automated | `data/raw` | Nenhuma imagem de amostra encontrada para smoke test. |
| QA-08 | Dataset | attention | automated | `reports/dataset_readiness/dataset_readiness.md` | Raw: 0; curado: 0; faltam imagens brutas: 300. |
| QA-09 | Aceite do reconhecimento | pending | manual_required | `/workspace/work/ecoscan/models/semantic-v1/semantic.json` | A existência do artefato não aprova o modelo. Exige contrato de preparo compatível, teste independente, métricas por classe e decisão de promoção registrada. |
| QA-10 | Erros | ok | automated | `src/ecoscan/errors.py` | Contrato público contém código, título, mensagem, ação, categoria e catálogo de erros principais. |
| QA-16 | Campanha e denúncias | ok | static | `config/campaigns.json; src/ecoscan/services/campaigns.py; src/ecoscan/services/civic_reports.py` | 7 missão(ões) e 3 recompensa(s) configuradas; serviço de denúncia presente. Não comprova persistência compartilhada. |
| QA-17 | Perfis e gestão | attention | static | `config/user_profiles.json; src/ecoscan/services/accounts.py; src/ecoscan/ui/streamlit_app.py` | 2 perfil(is) de demonstração; usuário=True, admin=True. Não verifica contas Supabase, autorização real nem persistência. |
| QA-11 | Interface | attention | static | `streamlit_app.py e live_camera/server.py` | Marcadores de interface parcialmente encontrados; verificar refatorações e teste funcional. |
| QA-18 | Identidade real | pending | manual_required | `docs/roadmap_entrega.md: etapa 1` | Executar cadastro, confirmação, isolamento entre duas contas, revisão e recuperação na nuvem. |
| QA-19 | Persistência integrada | pending | manual_required | `docs/roadmap_entrega.md: etapa 1` | Validar ativação da migração 003, campanhas e relatos entre contas, reinício e falha do banco. Testes locais não comprovam operação publicada. |
| QA-20 | Dispositivos | pending | manual_required | `docs/roadmap_entrega.md: etapa 1` | Validar celular e computador reais; câmera Live possui implantação separada. |
| QA-21 | Operação e recuperação | pending | manual_required | `docs/roadmap_entrega.md: etapa 3` | Ensaiar restauração de backup e retorno de versão; definir retenção e responsável pelo suporte. |
| QA-06 | Dependência ausente | pending | not_executed | `Modelo e imagem de amostra` | Verificação não executada. Consulte a falha ou dependência indicada nos itens anteriores. |
| QA-07 | Dependência ausente | pending | not_executed | `Modelo e imagem de amostra` | Verificação não executada. Consulte a falha ou dependência indicada nos itens anteriores. |
