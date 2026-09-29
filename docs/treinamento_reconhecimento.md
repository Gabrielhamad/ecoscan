# Treinamento e preparação do reconhecimento

Este é o procedimento oficial para incorporar novas imagens ao EcoScan. O fluxo
é deliberadamente supervisionado: uma foto reportada pode melhorar a próxima
rodada, mas nunca altera o modelo usado pelos participantes automaticamente.

## O que acontece antes do reconhecimento

Cada imagem passa pelo mesmo pipeline registrado no resultado da análise:

1. validação, orientação EXIF, RGB com transparência sobre branco e redução proporcional;
2. diagnóstico da captura, incluindo percentis de brilho, contraste e ruído;
3. correção condicional entre controle sem filtro, Gaussiano, mediana seletiva,
   bilateral e CLAHE suave, com limites de preservação;
4. segmentação auxiliar entre Otsu, GrabCut ou ausência de máscara confiável;
5. abertura/fechamento morfológico da máscara e análise de componentes;
6. RGB completo com margens para o classificador, sem apagar pixels pela máscara.

Perfil atual: [RGB preservado v2](processamento_preservado_v2.md), de 29/09/2026.
O artefato legado não foi retreinado nesta revisão; hipóteses ficam não confirmadas
até existir um candidato compatível e validado. HSV é um experimento manual.

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
- rejeita capturas com qualidade insuficiente; falha da máscara auxiliar não elimina uma foto útil;
- gera novamente treino, validação e teste;
- compara classificadores visuais supervisionados e seleciona pelo macro-F1 de validação;
- grava o manifesto e as métricas em
  `reports/recognition_training_candidate`;
- salva o modelo em `models/vision_svm_classifier_candidate.joblib` (nome legado;
  o algoritmo selecionado é registrado no relatório);
- salva o contrato de preparação em `models/vision_svm_classifier_candidate.joblib.processing.json`;
- **não substitui o modelo ativo**.

Para comparar outra configuração experimental do classificador sem refazer a preparação:

```powershell
python scripts\train_visual_svm.py `
  --output-model models\vision_svm_classifier_candidate.joblib `
  --report-dir reports\recognition_svm_candidate `
  --threshold 0.35
```

Esse script isolado não certifica a preparação dos splits nem emite o contrato;
seu resultado não deve ser promovido diretamente. Para uma rodada rastreável,
use o ciclo completo acima. `--overwrite` reconstrói diretórios processados e
splits: preserve previamente o manifesto e os dados necessários da rodada anterior.

O limiar maior aumenta a abstenção, mas não prova maior precisão. O número de imagens aceitas
deve ser lido junto com precisão, recall, macro-F1 e matriz de confusão.
O ciclo padrão usa limiar `0.25`, igual ao modelo do piloto. A preparação
salva o RGB integral ajustado em PNG sem perdas; o classificador extrai dele os
mesmos atributos usados na inferência. A configuração do pipeline e o hash
do candidato são registrados em `training_run.json`. Nunca reutilize como
originais as imagens antigas que já tiveram partes removidas por máscaras.

O split automático agrupa duplicatas exatas, mas ainda não separa por objeto,
cena ou sessão. Mantenha um teste de campo independente, sem cenas do treino.
O mínimo de 20 imagens é apenas uma barreira operacional, não suficiência estatística.

## Critério de aprovação

Antes de promover qualquer candidato, o analista deve conferir:

- classes do artefato exatamente iguais às classes de `config/settings.json`;
- contrato da preparação e hash do artefato compatíveis; promover ambos os arquivos juntos;
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
