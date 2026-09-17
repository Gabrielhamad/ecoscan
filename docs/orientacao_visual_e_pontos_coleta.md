# Orientação visual, descarte e pontos de coleta

## Objetivo de produto

O EcoScan deve ajudar uma pessoa a sair da dúvida no momento do descarte. Depois da foto, a resposta precisa ser prática: material identificado, preparo recomendado, cor da lixeira ou ponto de entrega, busca por local próximo e consequência do descarte incorreto.

A aplicação também pode ser usada por uma Secretaria do Meio Ambiente, escola, condomínio ou projeto de extensão como canal educativo e como base para organizar campanhas de coleta seletiva e logística reversa.

## Fluxo implementado

1. O usuário abre o app no PC ou celular.
2. A entrada padrão é câmera, com upload de imagem como alternativa.
3. O sistema aplica pré-processamento, filtragem adaptativa e segmentação adaptativa.
4. O reconhecimento retorna classe, confiança e estado de aceitação.
5. Quando a confiança é suficiente, o EcoScan exibe destino recomendado, passos de preparo, alerta de cuidado, impacto ambiental e links para buscar pontos próximos.
6. O modo EcoScan Live prioriza câmera traseira no celular, executa reconhecimento contínuo e rastreia visualmente os componentes segmentados.
7. A aba Pontos de coleta consulta a base local cadastrada e filtra locais compatíveis com o material.

## Destino por classe

As classes ativas cobrem recicláveis comuns e resíduos especiais:

| Classe | Destino exibido | Busca sugerida |
|---|---|---|
| Plástico | Lixeira vermelha | ponto de coleta seletiva plástico reciclagem |
| Papel / papelão | Lixeira azul | ponto de coleta seletiva papel papelão reciclagem |
| Metal | Lixeira amarela | ponto de coleta seletiva metal reciclagem |
| Vidro | Lixeira verde | ponto de coleta seletiva vidro reciclagem |
| Orgânico | Lixeira marrom | compostagem comunitária coleta resíduos orgânicos |
| Pilha / bateria | Ponto de coleta especial | ponto de coleta pilhas baterias descarte |
| Eletrônico | Ponto de logística reversa | ponto de coleta lixo eletrônico eletroeletrônicos |

Classes especiais já ficam estruturadas em configuração: lâmpadas, medicamentos, óleo de cozinha, aerossóis e embalagens químicas. Elas podem orientar descarte e receber imagens, mas só devem ser tratadas como reconhecimento confiável depois que a base tiver volume, curadoria e avaliação suficientes.

## Impacto ambiental

O arquivo `config/environmental_impacts.json` separa as consequências do mau descarte por classe. Essa decisão deixa o conteúdo revisável sem precisar treinar novamente o modelo.

Cada classe possui:

- título de impacto;
- nível de risco;
- riscos do descarte incorreto;
- ação positiva;
- fonte de referência.

Exemplos:

- pilhas e baterias aparecem como resíduo especial de alto risco;
- eletroeletrônicos aparecem como logística reversa;
- óleo de cozinha aparece com risco de poluição hídrica e entupimento;
- papel e papelão aparecem com foco em perda de reciclabilidade quando úmidos ou contaminados.

## Papel institucional

Usuário comum:

- tira foto do resíduo;
- entende onde descartar;
- aprende como preparar o material;
- busca ponto próximo;
- entende o dano de um descarte incorreto.

Secretaria, escola ou instituição:

- revisa textos ambientais;
- mantém base de ecopontos;
- direciona campanhas por categoria;
- valida regras municipais;
- acompanha dúvidas frequentes pela evolução futura do histórico.

## Base local de ecopontos

O arquivo `config/collection_points.json` cadastra pontos de coleta com endereço, bairro, horário, materiais aceitos, fonte e observações. A base inicial usa os ecopontos informados pela página Recicla Ribeirão Preto.

Campos principais:

- `accepted_classes`: classes do EcoScan aceitas pelo ponto;
- `accepted_materials`: descrição pública dos materiais aceitos;
- `hours`: funcionamento;
- `source_url`: origem da informação;
- `latitude` e `longitude`: opcionais para ordenação interna por distância.

Na versão atual, quando as coordenadas ainda não estão cadastradas, o app gera links de rota e busca no Google Maps. Quando a instituição adicionar latitude e longitude oficiais, o mesmo serviço passa a ordenar pontos por proximidade dentro do sistema.

## Referências usadas

- CONAMA, Resolução nº 275/2001, padrão de cores para coleta seletiva: https://conama.mma.gov.br/index.php?id=1356&option=com_sisconama&view=processo
- SINIR, logística reversa e gestão de resíduos: https://sinir.gov.br/perfis/logistica-reversa/
- SINIR, informações gerais sobre resíduos sólidos: https://sinir.gov.br/
- Recicla Ribeirão Preto, ecopontos e materiais aceitos: https://www.ribeiraopreto.sp.gov.br/recicla/ecopontos

## Evolução profissional

A busca atual usa Google Maps por texto, sem chave de API. Isso reduz dependência técnica e permite demonstrar a funcionalidade localmente.

Em versão institucional, o próximo passo é adicionar uma base municipal de pontos de coleta com latitude, longitude, endereço, horário, tipos aceitos e responsável. Com isso, o app pode ordenar pontos por distância, filtrar por material e exibir informações oficiais sem depender de busca externa.
