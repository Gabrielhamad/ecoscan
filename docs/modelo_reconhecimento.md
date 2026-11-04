# Modelo de reconhecimento

## Release ativa

O runtime usa somente `semantic_onnx_assisted`, configurado em `config/settings.json`.

| Componente | Arquivo |
| --- | --- |
| Metadados, classes, limiar e hashes | `models/semantic-v1/semantic.json` |
| Cabeça supervisionada | `models/semantic-v1/head.npz` |
| Encoder congelado | partes `encoder_*.part`, reconstruídas e verificadas localmente |
| Licença do encoder | `models/semantic-v1/LICENSE-CLIP` |
| Base de atualização | `learning_seed.json` e `learning_seed.npz` |

O formato atual é CLIP ViT-B/32 QuickGELU exportado para ONNX FP16, com uma cabeça supervisionada sobre as seis classes do piloto e a classe `unknown`.

## Comportamento seguro

O classificador pode aceitar internamente uma hipótese pelo limiar do artefato. O produto converte essa saída em sugestão assistida e exige confirmação. A previsão não autoriza automaticamente:

- orientação definitiva de descarte;
- pontos em missões;
- confirmação de composição, contaminação ou conteúdo;
- uso como detecção de múltiplos objetos.

Essa política fica em `services/analysis_service.py` e `services/recognition_safety.py`, fora do modelo.

## Evidência disponível

Na avaliação histórica registrada junto à release, houve 97 correspondências de primeira escolha em 145 imagens. Entre 50 resultados acima do limiar, 47 estavam corretos. Essa medição reutiliza um conjunto histórico e não comprova desempenho em fotos novas de produção.

Metal, plástico e vidro são prioridades de validação. A próxima avaliação precisa separar cenas, objetos e pessoas de captura, registrar precisão, recall, F1, rejeição e confusões por classe.

## Atualização

1. O participante envia uma correção com consentimento.
2. Um analista revisa foto, item e classe.
3. O executor privado verifica proveniência, duplicatas e separação dos dados.
4. A cabeça candidata é ajustada; o encoder permanece congelado.
5. O candidato é comparado com a release ativa na mesma validação.
6. A publicação só ocorre se os gates globais e por classe forem atendidos.
7. O app baixa a release, valida revisões, hashes e contrato antes de usá-la.

Não há treino local alternativo na interface e não há fallback para KNN, SVM, TensorFlow ou arquivos selecionados por extensão.

## Critério para automatizar uma classe

A confirmação só deve deixar de ser obrigatória após uma avaliação independente e versionada demonstrar, para a classe:

- suporte representativo de cenários reais;
- precisão e recall compatíveis com o risco da orientação;
- ausência de regressão nos casos difíceis conhecidos;
- calibração do limiar e taxa de rejeição aceitável;
- teste no celular e nas condições reais do piloto;
- aprovação explícita da gestão do produto.
