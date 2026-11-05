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

Na reprodução da avaliação histórica registrada junto à release, houve 101
correspondências de primeira escolha em 145 exemplos (69,7%). O limiar aceitou
51 resultados: 47 corretos, 4 incorretos e 94 rejeitados. O comando
`python scripts/evaluate_bundled_model.py` verifica os hashes e recalcula o
[relatório versionado](model_evaluation/semantic_v1_historical.json).

| Classe prioritária | Top-1: precisão / recall | Acima do limiar: precisão / recall |
| --- | --- | --- |
| Metal | 78,6% / 75,9% | 100,0% / 48,3% |
| Plástico | 65,7% / 82,1% | 93,8% / 53,6% |
| Vidro | 79,3% / 79,3% | 90,0% / 31,0% |

O limiar reduz erros, mas rejeita muitas imagens, principalmente de vidro. Essa
medição reutiliza vetores históricos usados durante o desenvolvimento. As fotos,
objetos e sessões originais não acompanham o clone, portanto não é possível
reauditar vazamento por cena. Os 16 hashes reservados também não possuem vetores
e rótulos versionados. Estes números não comprovam desempenho em fotos novas.

Metal, plástico e vidro são prioridades de validação. A próxima avaliação precisa separar cenas, objetos e pessoas de captura, registrar precisão, recall, F1, rejeição e confusões por classe.
O [protocolo para fotos reais](avaliacao_campo.md) descreve o manifesto com IDs de objeto/sessão, controle de hashes e avaliação reproduzível. A auditoria de metadados não certifica por si só a independência das fotos.

O recorte TACO preservado no repositório contém 23 crops, todos de treino:
9 plásticos, 7 metais e 7 papéis, em 20 grupos. Ele não contém vidro e não pode
ser promovido a teste independente da release atual.

## Diagnóstico externo TrashNet

Como as APIs Wikimedia e Openverse estavam bloqueadas pelo proxy do ambiente,
o acervo TrashNet foi obtido pelo GitHub no commit
`6fa2b878c6c1b4304b91109070ce0edf9279bb31`. Foram avaliadas apenas as 224
imagens de metal, plástico e vidro do split oficial de teste:

| Classe | Suporte | Top-1: precisão / recall | Acima do limiar: precisão / recall |
| --- | ---: | --- | --- |
| Metal | 68 | 89,7% / 89,7% | 100,0% / 69,1% |
| Plástico | 74 | 86,8% / 79,7% | 100,0% / 27,0% |
| Vidro | 82 | 84,6% / 80,5% | 100,0% / 32,9% |

No total, houve 186/224 primeiras escolhas corretas. O limiar aceitou 94 e
rejeitou 130; os 94 aceitos estavam corretos nesse recorte. O
[relatório](model_evaluation/trashnet_priority_diagnostic.json) e o
[manifesto com hashes](model_evaluation/trashnet_priority_manifest.json) estão
versionados, sem copiar as imagens.

Este resultado é diagnóstico, não teste independente: uma origem histórica em
comum não pode ser descartada, o TrashNet não fornece grupos por objeto/sessão e
as fotos usam fundo branco. O benchmark não mede cenas reais, resíduos
amassados, múltiplos objetos nem rejeição fora do escopo. Nenhuma decisão de
treino ou limiar foi tomada com esse resultado.

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
