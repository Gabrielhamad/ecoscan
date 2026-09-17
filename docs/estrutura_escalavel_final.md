# Estrutura escalável para a fase final

Este documento resume a organização profissional preparada para o EcoScan crescer sem virar um arquivo único difícil de manter.

## Decisão de engenharia

A interface Streamlit deve ficar responsável por renderizar telas e receber ações do usuário. Regras de negócio, agregações, prontidão final, campanhas, contas, denúncias, dataset e reconhecimento devem ficar em `src/ecoscan/services` ou nos pacotes específicos de domínio.

## Núcleos atuais

| Área | Módulo | Responsabilidade |
|---|---|---|
| Análise de imagem | `src/ecoscan/services/analysis_service.py` | Orquestra validação, processamento, segmentação, classificação e orientação. |
| Processamento | `src/ecoscan/image_processing` | Filtros, qualidade, redimensionamento, captura e filtragem adaptativa. |
| Segmentação | `src/ecoscan/segmentation` | Otsu, HSV, GrabCut, máscara, elementos e mapa visual. |
| Reconhecimento | `src/ecoscan/classification` | Inferência, regras de material e carregamento de modelos. |
| Operação pública | `src/ecoscan/services/campaigns.py` | Missões, recompensas e validação de evidência. |
| Fluxo público mobile | `src/ecoscan/services/public_flow.py` | Próxima ação para o cidadão após reconhecimento, com destino, confiança, preparo e busca de ponto. |
| Operação da secretaria | `src/ecoscan/services/operations.py` | Indicadores de campanha, cobertura territorial, missões publicadas e desempenho. |
| Melhoria do reconhecimento | `src/ecoscan/services/recognition_improvement.py` | Priorização de classes, confusões críticas, testes de campo e ações para reforçar a base de imagens. |
| Usuários e pontos | `src/ecoscan/services/accounts.py` | Perfis locais, pontuação, ranking e livro de transações. |
| Denúncias | `src/ecoscan/services/civic_reports.py` | Registro de mau descarte, evidência e revisão administrativa. |
| Pontos de coleta | `src/ecoscan/disposal/collection_points.py` | Base oficial filtrável por cidade, material e endereço. |
| Dataset | `src/ecoscan/services/dataset_*` | Entrada, revisão, curadoria, split e prontidão de treino. |
| Acesso e testes | `src/ecoscan/services/access_plan.py` | Links local/rede, status dos serviços e roteiro para teste em grupo. |
| Testes de campo | `src/ecoscan/services/field_testing.py` | Registro de resultados por colega, classe, dispositivo, acerto, erro e inconclusivo. |
| Hospedagem gratuita | `src/ecoscan/services/deployment_readiness.py` | Checklist de publicação HTTPS gratuita, arquivos exigidos e limitações do modo gratuito. |
| Governança do modelo | `src/ecoscan/services/model_governance.py` | Critérios de promoção, métricas comparativas e casos difíceis de regressão antes de trocar o modelo ativo. |
| Prontidão final | `src/ecoscan/services/final_readiness.py` | Trilhas de conclusão, implantação, segurança e evolução futura. |

## Fluxo profissional

1. O usuário escaneia ou envia uma foto.
2. O pipeline aplica validação, filtros adaptativos, segmentação e reconhecimento.
3. O app exibe primeiro a próxima ação do cidadão: material, confiança, destino, preparo e busca de ponto próximo.
4. A evidência visual do processamento fica disponível como detalhe técnico para transparência acadêmica.
5. Se participar de missão, a evidência pontua no livro de transações.
6. Se houver erro de reconhecimento, a correção entra no ciclo de melhoria do dataset.
7. A secretaria acompanha missões, ranking, denúncias, pontos de coleta, classes problemáticas e prontidão final.

## Pontos preparados para depois

- Trocar perfis locais por autenticação real.
- Publicar o app principal no Streamlit Community Cloud para testes em HTTPS.
- Publicar o EcoScan Live em backend HTTPS dedicado se a detecção ao vivo contínua for exigida fora da rede local.
- Usar a aba Sistema para rodadas controladas de teste por celular/PC antes da publicação.
- Usar os registros de teste de campo para priorizar fotos e medir evolução antes/depois.
- Usar correções de reconhecimento como lote de curadoria.
- Treinar novo modelo apenas após dataset revisado.
- Promover modelo somente com avaliação comparativa, ganho mínimo e passagem nos casos difíceis de regressão.
- Conectar base oficial de coleta por API ou base municipal atualizada.
- Evoluir de classificação do frame para detecção múltipla por objeto.

## Regra para novas melhorias

Quando adicionar uma funcionalidade nova:

1. Criar regra de negócio em `src/ecoscan/services` ou no pacote de domínio correto.
2. Deixar a UI apenas chamando esse serviço.
3. Adicionar teste unitário no serviço.
4. Atualizar `acceptance_checks.py` se a funcionalidade for parte da entrega.
5. Atualizar docs apenas quando o fluxo de uso ou arquitetura mudar.
