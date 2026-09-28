# Checklist APS

A presença de uma funcionalidade abaixo não equivale a aceite real nem a qualidade
de reconhecimento comprovada. Consulte a [avaliação atual](avaliacao_e_entrega.md)
e confronte esta lista com o enunciado oficial da instituição.

## Implementado

- aquisição por upload;
- aquisição por câmera na interface;
- captura por webcam via OpenCV quando instalado;
- detecção por câmera na interface após captura;
- modo ao vivo para celular com preferência por câmera traseira;
- tracking visual de elementos segmentados com IDs estáveis;
- script de webcam com captura, inferência e evidências;
- validação de imagem;
- manipulação RGB;
- redimensionamento;
- normalização;
- filtros;
- segmentação;
- morfologia binária: erosão, dilatação, abertura, fechamento e abertura seguida de fechamento;
- elemento estruturante configurável, estágios intermediários e gradiente morfológico para inspeção;
- laboratório com tons de cinza, histogramas, normalização e comparação de máscaras;
- experimento sintético com referência conhecida e IoU, sem confundir com acurácia de reconhecimento;
- análise de qualidade antes/depois do filtro;
- análise de componentes/elementos visuais segmentados;
- visualização do pipeline;
- base de orientações separada;
- baseline;
- divisão treino/validação/teste;
- avaliação com métricas;
- matriz de confusão exportável;
- histórico local;
- logging técnico de inferências e falhas;
- tratamento de erro de modelo ausente;
- tratamento de imagem inválida;
- tratamento de erros padronizado com código, mensagem e ação recomendada;
- catálogo documentado de erros operacionais;
- documentação técnica;
- documentação acadêmica;
- plano de transfer learning;
- interface Streamlit;
- visão geral executiva no topo da interface;
- barras visuais de confiança por classe;
- roadmap profissional;
- diagnóstico de dependências/modelo/dataset;
- exportação de evidência técnica pela interface;
- upload múltiplo de imagens para o dataset bruto;
- manifesto de uploads com hash, classe e status;
- relatório de prontidão do dataset por classe;
- bloqueio de duplicatas exatas;
- script de importação de pasta para novas fotos do grupo;
- orientações preparadas para classes futuras de resíduos especiais;
- auditoria de requisitos da APS com score de prontidão;
- aba de status com gates de engenharia;
- relatório acadêmico consolidado gerável por script/interface;
- exportação de overlay com caixas dos elementos visuais.
- validação executável dos critérios principais da APS.
- interface mobile/live com painel moderno e controles tocáveis.

## Depende de dataset maior/limpo

- métricas confiáveis;
- escolha final entre MobileNetV2, EfficientNetB0 e ResNet50;
- calibração real do limiar de confiança;
- comparação final de filtros/segmentação;
- treinamento final;
- conclusão estatística do relatório;
- inclusão oficial de novas classes além das ativas;
- modelo final `.keras`;
- auditoria final após dataset curado.
- relatório final revisado pelo grupo.

## Fora do MVP

- detecção treinada de múltiplas classes por objeto na mesma imagem;
- YOLO/detecção supervisionada por caixas;
- localização automática por proximidade com coordenadas verificadas (há consulta a uma base limitada e links de mapas);
- aplicativo mobile nativo (a interface web possui uso em celular, sujeito a aceite nos dispositivos).

Roteiro de demonstração e critérios experimentais: [prática de processamento](pratica_processamento_imagens.md).
