# Protocolo de avaliação com fotos reais

## Objetivo e limites

Avaliar o reconhecedor ONNX ativo em fotos novas de **metal, plástico e vidro**
capturadas no ambiente do piloto, sem ajustar o modelo com essas mesmas fotos.
O diagnóstico TrashNet registrado no projeto é histórico e **não** substitui
esta avaliação. Nenhum resultado pode ser chamado de desempenho de produção
apenas por passar na auditoria do manifesto.

## Coleta e separação

1. Definir classes e critérios de inclusão **antes** de fotografar. Obter permissão
   de uso, evitar rostos, placas, endereços e outros dados pessoais.
2. Registrar fotos com diferentes celulares, iluminação, fundo, ângulo e
   estado do objeto, inclusive reflexos e embalagens deformadas.
3. Identificar cada objeto físico por `object_id` e cada sessão de captura por
   `session_id`. Esses IDs devem ser únicos em todas as origens combinadas.
4. Nunca distribuir imagens do mesmo objeto **ou da mesma sessão** entre
   treino, validação e teste. Definir o split antes de olhar as previsões.
5. Conferir SHA-256 e duplicatas contra os arquivos de desenvolvimento
   disponíveis. Se o histórico de treino não puder ser auditado, declarar
   explicitamente essa limitação; não afirmar independência comprovada.
6. Congelar o conjunto de teste (arquivos, manifesto e hashes) antes da
   execução. Guardar as fotos fora do repositório público.

## Manifesto JSON

Um arquivo `reports/field/manifest.json` deve listar as imagens do teste e,
quando disponíveis, os registros de treino/validação usados na comparação de
grupos. Cada registro contém pelo menos:

```json
[
  {
    "path": "metal/lata_001.jpg",
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "class_id": "metal",
    "split": "test",
    "object_id": "obj-lata-001",
    "session_id": "celular-a-dia-01"
  }
]
```

Os hashes acima são **apenas ilustrativos**. Substitua-os pelos SHA-256 reais.
`path` é relativo à pasta fornecida em `--source`, sem caminhos absolutos ou
`..`. Valores aceitos de `split`: `train`, `validation`, `test`.
Todos os registros precisam de `object_id` e `session_id` quando usada a
opção `--require-groups`. Registros históricos que não contenham esses IDs
não devem ser inventados.

Opcionalmente, crie `reports/field/development_hashes.json` com uma lista JSON
dos hashes de imagens conhecidas usadas no desenvolvimento. O programa impede
que qualquer hash de teste conste nessa lista. Isso **não** comprova ausência
de sobreposição com dados históricos inacessíveis.

## Avaliação reproduzível

Instale as dependências e crie um arquivo `reports/field/cases.csv` com o
cabeçalho `path,expected_class` (linhas adicionais são opcionais). Os caminhos
dos casos de regressão são interpretados a partir do diretório atual.

```bash
python scripts/validate_semantic_onnx.py \
  --model models/semantic-v1/semantic.json \
  --manifest reports/field/manifest.json \
  --source data/field \
  --cases reports/field/cases.csv \
  --output reports/field/avaliacao.json \
  --require-groups \
  --development-hashes reports/field/development_hashes.json
```

Se não houver lista de hashes de desenvolvimento, **omita somente** a opção
`--development-hashes` e informe que a sobreposição histórica não foi
verificada. O script checa caminhos, duplicatas e hashes declarados antes
da inferência, e relata suporte por classe, precisão, recall, F1, matriz de
confusão, aceitação e rejeição. O campo `independent_test` permanece
`false` deliberadamente: a independência exige também auditoria humana
da proveniência e dos grupos que não constam do Git.

**Importante:** os registros de treino e validação usados apenas na auditoria
de grupos não são processados pelo classificador; somente as linhas com
`split: test` entram no cálculo das métricas.

## Evidência necessária para a APS

Documentar a versão do Git, hashes do modelo e do processamento, data,
responsável, origem das fotos, dispositivos, critérios de seleção, contagem por
classe, matriz de confusão, acertos, erros e rejeições. Apresentar separadamente
os resultados em vidro transparente, plástico transparente e metal refletivo,
sem deduzir o material somente pela transparência. Anexar imagens de
antes/depois e casos errados **somente com permissão**.

Se uma classe falhar, manter confirmação humana e registrar a falha como
limitação. Não ajustar o limiar ou a cabeça supervisionada usando o conjunto
de teste que será usado para aprovar essa mesma release.

## Testes automáticos

```bash
python -m pytest tests/test_evaluation_manifest.py tests/test_external_benchmark_evidence.py -q
```

A auditoria do manifesto verifica invariantes dos metadados; ela não substitui
as medições em novos aparelhos nem valida resultados que ainda não existem.
