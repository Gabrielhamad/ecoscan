# Roadmap profissional do EcoScan

## Visão

EcoScan é um guia inteligente de descarte responsável. A proposta é unir processamento digital de imagens, segmentação, reconhecimento visual e orientação ambiental em uma experiência útil para usuário comum, ambiente escolar, condomínio ou Secretaria do Meio Ambiente.

O produto não deve parecer apenas uma tela de trabalho acadêmico. A interface principal precisa responder perguntas reais:

- o que é este resíduo;
- qual é a confiança da leitura;
- que tratamento de imagem foi aplicado;
- onde descartar;
- como preparar o material;
- onde procurar um ponto próximo;
- quais são as consequências do mau descarte.

## Princípio de engenharia

O reconhecimento visual depende do dataset. Como as fotos definitivas serão adicionadas depois, a evolução atual foca em estrutura profissional, experiência de uso, governança do dataset, rastreabilidade técnica, tratamento de erros e orientação ambiental configurável.

## Marco 1: Produto mínimo demonstrável

Status: concluído.

Entregas:

- estrutura modular em Python;
- configuração centralizada;
- upload de imagem;
- câmera via navegador;
- validação de imagem;
- baseline de reconhecimento;
- rejeição por baixa confiança;
- orientação de descarte por classe;
- relatórios e scripts reprodutíveis.

Critério de aceite:

- usuário consegue enviar uma imagem válida;
- sistema responde com classe, confiança e orientação;
- erro de arquivo inválido aparece de forma clara.

## Marco 2: Processamento de imagem profissional

Status: concluído.

Entregas:

- redimensionamento e normalização;
- filtros Gaussiano, mediana, bilateral, CLAHE, Sobel e Canny;
- filtragem adaptativa com comparação automática de sequências;
- segmentação por Otsu, HSV e GrabCut;
- escolha adaptativa de segmentação;
- análise de componentes conectados;
- visualização da máscara e dos elementos detectados;
- resumo por foto informando filtro, segmentação, qualidade e elementos.

Critério de aceite:

- cada imagem analisada mostra qual filtragem e segmentação foram escolhidas;
- a decisão técnica fica disponível para relatório e apresentação.

## Marco 3: Experiência mobile e desktop

Status: em evolução, com base implementada.

Entregas atuais:

- layout responsivo no Streamlit com identidade visível da Secretaria do Meio Ambiente;
- linguagem visual de portal municipal ambiental, sem copiar marca oficial de governo;
- experiência pública simplificada para cidadão e experiência administrativa separada para gestão;
- entrada padrão por câmera;
- upload como alternativa;
- botão dinâmico para abrir o EcoScan Live no mesmo host/IP;
- modo live com preferência por câmera traseira;
- overlay de rastreamento por componentes segmentados;
- painel compacto de classe, confiança, filtro e segmentação;
- destino recomendado e busca de ponto próximo.
- aba de pontos de coleta filtrável por material;
- base local inicial de ecopontos com endereço, horário, materiais aceitos e fonte.

Melhorias recomendadas:

- rodar o modo live com HTTPS local ou túnel seguro para liberar câmera em celular;
- transformar o Streamlit em uma versão web/PWA quando houver tempo;
- adicionar latitude e longitude oficiais aos pontos cadastrados para ordenação interna por distância;
- criar modo de demonstração offline com imagens de exemplo revisadas.

Critério de aceite:

- no PC, o app abre em `localhost`;
- no celular na mesma rede, o app abre pelo IP da máquina;
- o fluxo principal do usuário é tirar foto, ver destino e buscar ponto próximo.
- o usuário comum não recebe excesso de abas técnicas, enquanto o admin mantém acesso aos painéis de operação.

## Marco 4: Orientação ambiental útil

Status: concluído na estrutura, revisável pelo grupo.

Entregas:

- `config/disposal_guidance.json` para orientação de descarte;
- `config/disposal_targets.json` para cor, imagem, preparo e busca;
- `config/environmental_impacts.json` para consequências do mau descarte;
- imagens de referência de lixeira ou ponto de entrega;
- busca por cidade, bairro, CEP ou localização atual;
- busca geral por ecopontos próximos;
- fontes de referência separadas por classe.
- base local `config/collection_points.json` com ecopontos filtráveis por classe.

Critério de aceite:

- o usuário entende o que fazer com o resíduo;
- resíduos especiais como pilhas, baterias e eletrônicos não são tratados como recicláveis comuns;
- o app explica risco ambiental em linguagem simples.

## Marco 5: Dataset do grupo

Status: pendente das novas fotos.

O que coletar:

- plástico: garrafas PET, sacolas, potes, tampas, embalagens limpas e sujas;
- papel/papelão: folhas, jornais, caixas, papel amassado, papelão seco e contaminado;
- metal: latas de alumínio, aço, tampas metálicas e embalagens metálicas limpas;
- vidro: garrafas, potes, cacos protegidos, vidro transparente e colorido;
- orgânico: cascas, restos de alimento, folhas, borra de café;
- pilhas/baterias: pilhas AA/AAA, baterias pequenas, power bank, bateria estufada apenas se for seguro fotografar;
- eletrônicos: celular antigo, carregador, cabo, mouse, teclado, placa, controle remoto;
- futuras classes: lâmpadas, medicamentos, óleo de cozinha em garrafa, aerossóis e embalagens químicas.

Regras de coleta:

- mínimo recomendado: 50 imagens por classe ativa;
- ideal: 100 ou mais por classe para treino final;
- fotografar em fundos claros, escuros e reais;
- variar iluminação, distância, ângulo e estado do objeto;
- incluir exemplos difíceis e parecidos entre classes;
- evitar rostos, documentos, placas, dados pessoais e marcas como foco principal.

Critério de aceite:

- dataset balanceado;
- imagens revisadas;
- duplicatas removidas;
- classes futuras só ativadas após volume suficiente.

## Marco 6: Modelo final

Status: preparado, dependente do dataset.

Entregas previstas:

- curadoria para `data/curated`;
- split treino/validação/teste sem vazamento;
- treinamento MobileNetV2;
- avaliação por accuracy, precision, recall, F1 e matriz de confusão;
- calibração do limiar de confiança;
- exportação de `models/ecoscan_transfer.keras`;
- comparação com baseline.

Critério de aceite:

- modelo final supera a baseline;
- classes perigosas têm recall aceitável;
- o sistema mantém resposta incerta quando a confiança é baixa.

## Marco 7: Campanha, missões e denúncia

Status: concluído na estrutura, revisável pela instituição.

Entregas:

- campanha configurável em `config/campaigns.json`;
- perfis locais de usuário e admin em `config/user_profiles.json`;
- papel institucional da Secretaria do Meio Ambiente representado no app;
- missões educativas por tipo de resíduo;
- pontuação persistente por perfil e recompensas simbólicas;
- validação de missão por foto usando tratamento, segmentação e reconhecimento;
- denúncia de mau descarte com evidência visual;
- triagem técnica da denúncia com classe provável, qualidade da imagem, filtro e segmentação usados;
- aba `Conta` para o usuário acompanhar pontos e denúncias;
- aba `Gestão` para o admin acompanhar participação e registrar decisão sobre denúncias;
- histórico local em CSV para auditoria e apresentação.

Critério de aceite:

- usuário consegue participar de uma missão e entender por que a imagem foi aceita ou recusada;
- denúncia registrada não depende de julgamento manual invisível, pois guarda evidências técnicas;
- admin consegue revisar denúncia sem alterar o resultado técnico da visão computacional;
- regras de campanha podem ser alteradas sem mexer no classificador.

## Marco 8: Uso institucional ampliado

Status: futuro.

Entregas sugeridas:

- cadastro municipal completo de ecopontos;
- filtros por material aceito;
- horário, endereço e observações do ponto;
- coordenadas oficiais para cálculo de proximidade dentro do app;
- painel agregado de dúvidas frequentes;
- exportação de relatório para escola, condomínio ou secretaria;
- autenticação segura com login real, senha protegida e permissões de produção;
- painel administrativo com edição visual de missões, recompensas, campanhas e pontos oficiais;
- integração com campanhas públicas reais.

Critério de aceite:

- app orienta usuário e também apoia gestão ambiental;
- pontos exibidos são oficiais ou revisados;
- regras locais podem ser atualizadas sem mexer no modelo.

## Riscos principais

- dataset pequeno;
- classes visualmente parecidas;
- resíduos múltiplos na mesma foto;
- câmera mobile bloqueada por falta de HTTPS;
- iluminação ruim;
- excesso de classes antes de haver dados;
- regra local de descarte variar por cidade.

## Mitigações

- manter limiar de confiança;
- usar filtragem e segmentação adaptativas;
- registrar processamento usado por foto;
- documentar limitações;
- separar regras ambientais do modelo;
- revisar dataset antes do treino;
- ativar novas classes gradualmente;
- usar HTTPS ou túnel seguro no teste mobile ao vivo.

## Checklist de execução

Antes da apresentação ou entrega:

```powershell
python scripts\diagnose_project.py
python scripts\run_acceptance_checks.py
python scripts\project_audit.py
python scripts\project_status.py
python scripts\prepare_delivery_pack.py
python -m unittest discover -s tests
```

O ponto crítico restante é o dataset final. A estrutura está preparada para receber as fotos, revisar a base, treinar novamente e melhorar a eficiência do reconhecimento.
