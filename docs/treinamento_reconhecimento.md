# Treinamento e preparação do reconhecimento

Este é o procedimento oficial para incorporar novas imagens ao EcoScan. O fluxo
é deliberadamente supervisionado: uma foto reportada pode melhorar a próxima
rodada, mas nunca altera o modelo usado pelos participantes automaticamente.

## O que acontece antes do reconhecimento

Cada imagem passa pelo mesmo pipeline registrado no resultado da análise:

1. validação do arquivo, leitura RGB e redimensionamento;
2. avaliação da captura, incluindo brilho, contraste, nitidez e bordas;
3. escolha adaptativa do filtro mais adequado entre controle sem filtro,
   Gaussiano, mediana, bilateral e CLAHE;
4. seleção adaptativa da segmentação entre Otsu, HSV e GrabCut;
5. abertura/fechamento morfológico da máscara e análise de componentes;
6. criação da imagem realmente entregue ao classificador.

Na tela pública, **Processamento aplicado: antes e depois** mostra a imagem
original, o filtro escolhido, a máscara, a imagem segmentada, os componentes e
a prévia usada na classificação. Os parâmetros e as métricas são específicos
daquela foto; não são uma ilustração genérica.

Isso demonstra a técnica de processamento da disciplina, mas não transforma
uma máscara em prova de material. A classificação continua dependendo de dados
curados e de um modelo avaliado.

## Classes ativas

O escopo atual possui seis classes:

- `plastic`
- `paper_cardboard`
- `metal`
- `glass`
- `battery`
- `electronic`

Óleo de cozinha e medicamentos permanecem como orientação assistida. Orgânicos,
alimentos e classes perigosas não devem ser adicionados ao treino sem uma
decisão de escopo, orientação de descarte e volume mínimo de imagens.

## Ciclo seguro de treinamento

Depois de revisar as fotos da aba **Base de imagens** e colocá-las em
`data/curated/<classe>`, execute na raiz do projeto:

```powershell
python scripts\train_recognition_cycle.py --overwrite --min-quality-score 55 --min-per-class 20
```

O comando:

- prepara cada foto com o pipeline adaptativo;
- rejeita imagens com qualidade ou segmentação insuficiente;
- gera novamente treino, validação e teste;
- compara classificadores visuais supervisionados e seleciona pelo macro-F1 de validação;
- grava o manifesto e as métricas em
  `reports/recognition_training_candidate`;
- salva o modelo em `models/vision_svm_classifier_candidate.joblib` (nome legado;
  o algoritmo selecionado é registrado no relatório);
- **não substitui o modelo ativo**.

Para comparar outra configuração do classificador sem refazer a preparação:

```powershell
python scripts\train_visual_svm.py `
  --output-model models\vision_svm_classifier_candidate.joblib `
  --report-dir reports\recognition_svm_candidate `
  --threshold 0.35
```

O limiar maior aumenta a abstenção: em dúvida, o app pede uma nova foto em vez
de entregar uma orientação potencialmente errada. O número de imagens aceitas
deve ser lido junto com precisão, recall, macro-F1 e matriz de confusão.
O ciclo padrão usa limiar `0.25`, igual ao modelo do piloto. A preparação
salva a imagem segmentada em PNG sem perdas; o classificador extrai dela os
mesmos atributos usados na inferência. A configuração do pipeline e o hash
do candidato são registrados em `training_run.json`.

## Critério de aprovação

Antes de promover qualquer candidato, o analista deve conferir:

- classes do artefato exatamente iguais às classes de `config/settings.json`;
- teste independente, separado por objeto e cenário, sem duplicatas;
- matriz de confusão e métricas por classe;
- cobertura e precisão apenas entre respostas aceitas;
- desempenho em estados difíceis: lata amassada, garrafa deformada, papel
  dobrado, vidro quebrado, pilhas agrupadas e eletrônicos com cabos;
- exemplos desconhecidos, para verificar se o sistema sabe recusar;
- fotos reais de celular e estabilidade no modo ao vivo.

O carregador do serviço rejeita modelos com classes antigas ou sem metadados.
Essa falha explícita é intencional: evita que um artefato de uma rodada passada
produza um rótulo aparentemente válido no escopo novo.

## Como uma correção vira aprendizado

1. O participante envia uma análise e informa se a hipótese estava correta.
2. Com consentimento, a foto e o rótulo indicado entram em um protocolo.
3. A secretaria revisa, confirma ou rejeita o rótulo e registra a decisão.
4. As correções aprovadas são exportadas para curadoria; duplicatas e fotos
   ruins são removidas.
5. O grupo cria um novo split e roda o ciclo acima.
6. O candidato é comparado com o ativo e só então pode ser promovido por um
   responsável, com registro de versão e hash.

Uma aprovação humana é um rótulo supervisionado, não uma garantia de que todas
as imagens semelhantes terão o mesmo resultado. A base precisa continuar
variada por marca, cor, ângulo, distância, iluminação, deformação e fundo.

## Evidências da rodada

Cada rodada deve guardar, fora do código-fonte quando contiver fotos:

- `training_run.json`;
- manifesto de preparação;
- contagem por classe e por split;
- matriz de confusão e métricas;
- versão do código e hash do candidato;
- decisão de aprovação, rejeição ou necessidade de mais dados.

Fotos pessoais, tokens, cadastros e exportações privadas não devem ser enviados
ao GitHub. O conjunto publicado deve ter licença ou consentimento rastreável.
