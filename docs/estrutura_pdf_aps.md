# Estrutura seguida a partir das anotações da APS

## Direção do projeto

O EcoScan segue a ideia central das anotações: um sistema de educação ambiental fornecido por uma Secretaria do Meio Ambiente e usado por pessoas comuns para fotografar ou filmar resíduos, receber orientação de descarte e entender o impacto positivo da reciclagem.

## Mapeamento da anotação para o sistema

| Ideia da anotação | Implementação atual | Evidência |
|---|---|---|
| Usuário tira foto ou filma | Upload, câmera do navegador e EcoScan Live com câmera traseira | `src/ecoscan/ui/streamlit_app.py`; `src/ecoscan/live_camera/server.py` |
| Sistema edita a imagem automaticamente | Filtragem adaptativa, segmentação adaptativa e registro da decisão usada | `src/ecoscan/app/pipeline.py`; `reports/dataset_preparation/preparation_manifest.csv` |
| Sistema fala o que foi usado | Aba Processamento mostra filtro, segmentação, qualidade, elementos e metadados | `src/ecoscan/ui/streamlit_app.py` |
| Sistema faz reconhecimento | Baseline funcional com rejeição por baixa confiança | `models/baseline_classifier.json`; `reports/evaluation/baseline_test` |
| Mostrar onde e como descartar | Orientação, cor/lixeira/ponto, preparo e busca por ponto próximo | `config/disposal_guidance.json`; `config/disposal_targets.json` |
| Mostrar consequências do mau descarte | Painel de impacto ambiental por classe | `config/environmental_impacts.json` |
| Secretaria/Admin fala sobre campanha | Perfil administrativo, aba Campanha, aba Gestão e configuração editável | `config/user_profiles.json`; `config/campaigns.json` |
| Soltar missões | Missões rotativas com classe-alvo e dica de comprovação | `config/campaigns.json`; `src/ecoscan/services/campaigns.py` |
| Ter pontos | Validação de missão soma pontos persistentes por perfil | `src/ecoscan/services/accounts.py`; `reports/accounts/points_ledger.csv` |
| Organizar recompensas | Recompensas configuráveis por pontuação | `config/campaigns.json` |
| Denunciar mau descarte | Aba Denúncia salva evidência, perfil solicitante e manifesto local | `src/ecoscan/services/civic_reports.py` |
| Tratar veracidade da imagem recebida | Triagem usa validação, filtros, segmentação, reconhecimento, qualidade e elementos; admin registra decisão separada | `reports/civic_reports/reports_manifest.csv`; `reports/civic_reports/review_manifest.csv` |
| Expansão para lixeiras/pontos públicos | Planejado como evolução após modelo final e validação institucional | `docs/roadmap_profissional.md` |

## Leitura correta para apresentação

O projeto já demonstra o fluxo completo pedido: processamento de imagem, segmentação, reconhecimento, orientação de descarte, tratamento de erro e interface em Python. A camada de perfis, campanha, pontos e denúncia aproxima o app da proposta de uso real pela Secretaria.

A limitação principal continua sendo o reconhecimento final. A baseline existe para demonstrar integração e avaliação, mas a precisão confiável depende de completar e curar o dataset, depois treinar o modelo final por transfer learning.

## Próximo avanço técnico

1. Completar imagens das classes `medicine`, `cooking_oil`, `aerosol` e `chemical_packaging`.
2. Fazer curadoria em `reports/dataset_review/review_sheet.csv`.
3. Gerar `data/curated` e `data/processed`.
4. Treinar o modelo final.
5. Validar a campanha com regras reais de pontuação, recompensa, autenticação e encaminhamento de denúncia.
