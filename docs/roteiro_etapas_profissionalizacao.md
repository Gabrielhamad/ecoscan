# Roteiro em etapas para profissionalizar o EcoScan

Este roteiro organiza as próximas melhorias sem depender de um reconhecimento perfeito agora. A ideia é deixar o sistema útil, seguro e preparado para melhorar conforme o grupo testa e amplia o dataset.

## Etapa 1 - Uso seguro no dia a dia

Status: implementado.

- orientar o usuário antes da foto;
- diferenciar resultado seguro, provável e inconclusivo;
- não indicar descarte como certo quando a imagem estiver ruim ou a confiança for baixa;
- salvar metadados de análise para acompanhamento operacional;
- coletar correções de reconhecimento para reforçar o dataset.

Evidências:

- `src/ecoscan/services/recognition_safety.py`
- `src/ecoscan/services/usage_quality.py`
- aba `Gestão`, seção `Qualidade do reconhecimento`

## Etapa 2 - Ciclo de melhoria do dataset

Status: preparado e ligado à gestão.

- revisar correções enviadas pelos usuários;
- separar erros por classe confundida;
- priorizar fotos reais das classes com maior erro;
- usar testes de campo do grupo como evidência direta no plano de reforço;
- manter treino, validação e teste sem imagens repetidas;
- gerar relatório de antes/depois a cada novo treino.

## Etapa 3 - Experiência mobile

Status: implementado.

- deixar a ação de câmera/foto ainda mais central;
- reduzir controles técnicos para usuário comum;
- melhorar texto de orientação após reconhecimento;
- simplificar mapa e rota para ponto de descarte.

Evidências:

- `src/ecoscan/services/public_flow.py`
- aba `Escanear`, perfil `usuario_demo`
- cartão `O que fazer agora`
- detalhes técnicos recolhidos em expansores para o usuário comum

## Etapa 4 - Gestão da secretaria

Status: implementado como painel operacional.

- acompanhar campanhas, missões e pontuação;
- visualizar correções e classes problemáticas;
- priorizar classes para reforço com base em erro, baixa confiança e lacuna de imagens;
- separar confusões críticas do reconhecimento para orientar nova coleta de fotos;
- revisar denúncias com decisão administrativa;
- exportar relatórios operacionais;
- manter pontos oficiais de coleta atualizados.

Evidências:

- `src/ecoscan/services/operations.py`
- `src/ecoscan/services/recognition_improvement.py`
- aba `Gestão`, seção `Plano de reforço do reconhecimento`

## Etapa 5 - Implantação real

Status: teste em grupo e hospedagem gratuita preparados; produção institucional futura.

- disponibilizar links locais e de rede para teste por celular/PC;
- orientar limitações de HTTP, HTTPS e câmera ao vivo;
- conduzir rodada de testes com roteiro comum para os integrantes;
- registrar resultados da rodada por classe, dispositivo e tipo de erro;
- publicar o app principal gratuitamente em HTTPS para testes do grupo;
- publicar em HTTPS;
- autenticação OIDC e autorização administrativa implementadas; configurar credenciais e validar login real antes da publicação;
- proteger imagens e denúncias;
- criar política de retenção de evidências;
- conectar bases oficiais por API ou atualização controlada.

Evidências:

- `src/ecoscan/services/access_plan.py`
- `src/ecoscan/services/field_testing.py`
- `src/ecoscan/services/deployment_readiness.py`
- aba `Sistema`, seção `Acesso e rodada de testes`
- aba `Sistema`, seção `Hospedagem gratuita HTTPS`
- aba `Perfil`, seção `Registrar teste da rodada`

## Etapa 6 - Reconhecimento avançado

Status: governança preparada; treino final depende de dataset.

- treinar modelo final com dataset curado;
- promover modelo somente se superar métricas atuais;
- manter casos difíceis para regressão;
- evoluir para detecção múltipla por objeto quando houver rótulos adequados.

Evidências:

- `src/ecoscan/services/model_governance.py`
- aba `Conclusão`, seção `Governança do modelo final`
- uso de correções e testes de campo como casos difíceis de regressão

Critério profissional:

- o reconhecimento atual continua orientativo enquanto o dataset é reforçado;
- qualquer modelo novo precisa gerar relatório de avaliação separado;
- casos como lata reconhecida como vidro ou garrafa reconhecida como papel devem entrar na regressão obrigatória;
- o modelo final só deve ser promovido se superar a referência atual e passar nos casos difíceis.
