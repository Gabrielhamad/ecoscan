# Avaliação reproduzível com fotos locais

## Estado e limites

As ferramentas não incluem um conjunto de campo. Sem fotos locais fornecidas e
rotuladas, não há resultado de campo a apresentar. Fixtures sintéticas dos testes
validam contratos e aritmética; não medem acurácia do EcoScan. O histórico e o
TrashNet não substituem esta coleta.

`independent_test` permanece **false**, sem opção de CLI para promovê-lo. Validar
licença, consentimento declarado, hashes e grupos não comprova a origem ou a
independência: é necessária auditoria externa das imagens e do histórico de treino.
Não inventar IDs de objeto/sessão históricos que não possam ser recuperados.

## Coleta do grupo (07–08/11/2026)

1. Reservar **10–15 objetos físicos novos por classe prioritária**: metal, plástico
   e vidro (30–45 objetos), mais 5–10 objetos fora de escopo. É diagnóstico inicial,
   não certificação estatística. Usar `unknown` como rótulo de referência fora de
   escopo, não um material escolhido por semelhança. Conferir rótulo por inspeção
   humana; uma foto não comprova composição ou conteúdo.
2. Escolher uma foto principal por objeto **antes** de ver predições. Incluir
   fundos simples e complexos, iluminação difusa/sombra/reflexo, ângulos diferentes,
   objetos amassados e transparentes. Marcar `transparent_plastic`,
   `transparent_glass` e `reflective_metal` nos casos pertinentes. Preferir mais de
   um celular. Manter registro privado de dispositivo, data e responsável por sessão.
3. Obter autorização para avaliação local e conferir licença. Evitar pessoas,
   placas, endereços e fotos privadas de terceiros. Usar IDs opacos, sem nomes,
   e-mails ou RAs. `consent=true` é uma declaração conferida pelo grupo, não prova
   jurídica. Autorização de avaliação não implica autorização de publicação.
4. Definir `train`, `validation`, `test` antes da avaliação. Atribuir **objetos e
   sessões inteiros** a um único split; sessões com vários objetos devem permanecer
   juntas. Nunca reutilizar o mesmo objeto em treino e teste, mesmo em outra sessão.
   Se só há fotos novas de teste, usar todas como `test`, sem fabricar treino/validação.
   Incluir registros locais de desenvolvimento disponíveis para auditoria de grupos.
5. Manter fotos e registros de autorização fora do Git, preferencialmente fora do
   checkout. O CSV usa caminhos relativos à raiz privada. Congelar CSV, manifesto,
   fotos e hashes antes de rodar o classificador. Não selecionar apenas acertos.
6. Reservar dados de **validação** separados para escolher parâmetros. O teste final
   não serve para ajustar filtros, limiar ou cabeça. Fotos adicionais do mesmo
   objeto podem compor análise diagnóstica predefinida, mas não são objetos
   independentes. Os relatórios ponderam **imagens**, não objetos: usar uma foto
   principal por objeto no resultado principal e relatar correlação por sessão.

## CSV de coleta e geração de manifesto

Copiar o [CSV vazio](templates/coleta_campo.csv) para armazenamento local e preencher
uma linha por arquivo real. Ele contém só o cabeçalho; nenhum dado de campo fictício.

| Campo | Preenchimento obrigatório |
| --- | --- |
| `path` | Arquivo JPG/JPEG/PNG existente, relativo à raiz, sem `..`, caminho absoluto ou fuga via symlink |
| `class_id` | `metal`, `plastic`, `glass`, `paper_cardboard`, `battery`, `electronic` ou `unknown` |
| `split` | `train`, `validation` ou `test`, definido antecipadamente |
| `object_id`, `session_id` | Tokens opacos únicos na coleta combinada; mesmo objeto/sessão nunca atravessa splits |
| `license` | `private-consent`, `CC0-1.0`, `CC-BY-4.0` ou `CC-BY-SA-4.0`, conforme direito real de uso |
| `consent` | Literal `true` após conferência; ausência/`false` impede a avaliação |
| `source_kind` | `field_photo` para fotos reais fornecidas; `synthetic_fixture` somente em testes técnicos; não misturar |
| `scenario` | `standard`, `transparent_plastic`, `transparent_glass`, `reflective_metal` ou `out_of_scope` |
| `lighting`, `background`, `angle` | Tokens descritivos de até 64 caracteres, por exemplo `difusa`, `fundo_liso`, `frontal` |

Os cenários específicos devem corresponder ao rótulo (`out_of_scope` → `unknown`).
As demais colunas de token aceitam letras, números, ponto, hífen e underscore,
sem espaços. IDs não são inferidos de nomes de arquivo ou pastas.

Na raiz do repositório, com Python 3.12 e dependências instaladas:

```bash
mkdir -p reports/field
cp docs/templates/coleta_campo.csv reports/field/coleta.csv
```

Preencher o CSV com arquivos reais; definir a variável abaixo com a pasta privada
existente (o caminho é um placeholder, não um arquivo distribuído):

```bash
ECOSCAN_FIELD_ROOT='/caminho/privado/ecoscan-campo'
python scripts/build_field_manifest.py \
  --csv reports/field/coleta.csv \
  --source "$ECOSCAN_FIELD_ROOT" \
  --output reports/field/manifest.json
```

A CLI reutiliza o loader da aplicação: valida extensão, formato real, limites,
decodificação, orientação EXIF, transparência sobre branco e conversão RGB. Registra
hash do arquivo e hash do RGB orientado (shape/dtype + NUL + bytes C-order), dimensão
orientada, modo original e formato. Não exporta EXIF/GPS ou copia fotos.
Rejeita duplicatas por arquivo e por RGB decodificado, inclusive recodificações sem
perda. Imagens visualmente semelhantes/com perdas e IDs deliberadamente falsos
exigem revisão humana; nenhum hash garante detectar o mesmo objeto fotografado de novo.

O resultado é uma lista JSON conforme o
[modelo de manifesto](templates/manifesto_campo.schema.json). O schema descreve a
estrutura; a CLI também verifica arquivos, grupos e relações entre campos que o
schema isolado não comprova. Nada é gravado se a coleção estiver vazia/inválida;
manifesto existente não é sobrescrito.

Se houver hashes conhecidos de desenvolvimento, criar uma lista JSON local com
**hashes reais** e passar `--development-hashes reports/field/development_hashes.json`
tanto ao gerador quanto ao avaliador. Qualquer hash de teste presente nessa lista é
recusado. Sem a lista, declarar que o cruzamento histórico não foi realizado. A
separação de grupos é sempre verificada dentro dos registros fornecidos.

## Avaliar sem trocar a inferência

```bash
python scripts/validate_semantic_onnx.py \
  --model models/semantic-v1/semantic.json \
  --manifest reports/field/manifest.json \
  --source "$ECOSCAN_FIELD_ROOT" \
  --output reports/field/baseline.json
python -m pip freeze > reports/field/dependencies.txt
```

O comando mantém `run_processing_pipeline` + `SemanticOnnxClassifier.predict_image`;
não usa o serviço que força confirmação humana. O contrato padrão de processamento
e as classes devem coincidir com o modelo. Todos os arquivos de todos os splits são
validados antes do carregamento do encoder; só `test` entra na inferência/métricas.
Hashes e metadados são rechecados durante/finalizando a execução. Não há download de
fotos, envio para serviços ou alteração de modelo/limiar/safety gates.

O argumento antigo `--require-groups` continua aceito; grupos e proveniência agora
são obrigatórios, mesmo sem a flag. Manifestos antigos sem os campos novos devem
ser reconstruídos a partir de fotos/metadados reais; não completar consentimentos
ou grupos por inferência. Relatório JSON usa schema 3.

`--cases` tornou-se opcional. Caso usado, seu CSV `path,expected_class` deve indicar
somente um subconjunto de registros **já congelados em test**, relativo à raiz das
fotos, com o mesmo rótulo. Ele destaca erros/regressões no relatório sem recalcular
ou duplicar amostras. Caminhos novos, fora da raiz ou rótulos divergentes são recusados.

Para comparar um candidato autorizado no futuro, executar o mesmo comando com
`--model` apontando ao artefato candidato e outro `--output`. Conferir igualdade do
hash do manifesto e do contrato entre relatórios antes da comparação por classe.
Não ajustar candidato com o teste final e depois reutilizá-lo como prova independente.

## Relatórios e interpretação

`baseline.json` produz arquivos irmãos sem sobrescrever resultados existentes:

| Saída | Conteúdo |
| --- | --- |
| `.json` | Relatório completo, contrato, origem declarada, SHA Git/dirty, versões, hashes, métricas e predições |
| `.md` | Sumário, por classe, matriz, curva de seletividade, cenários, latência e integridade |
| `.csv` | N imagens/objetos/sessões por classe, precisão/recall/F1, rejeições e falsos positivos |
| `.summary.csv` | Top-1, macros, cobertura/erros nominais, hashes e latências agregadas |
| `.predictions.csv` | Índice no manifesto, hashes, rótulo real, `top_class_id`, score, classe aceita e tempos |
| `.confusion.csv` | Matriz top-1 completa, incluindo unknown e materiais preditos sem suporte real |
| `.selectivity.csv` | Cobertura, erros entre aceitos e rejeição em limiares fixos; nenhuma escolha automática |
| `.scenarios.csv` | Plástico/vidro transparente, metal refletivo, fora de escopo e controle padrão |

- Top-1 compara rótulo com `top_class_id`, **antes da confirmação humana**, inclusive
  nas predições rejeitadas. Aceitação usa `accepted/class_id` do classificador e o
  limiar do artefato (0,8 na baseline), não a decisão final da interface.
- Macros são médias das classes com suporte real > 0, incluindo `unknown` se
  observado. Classes não coletadas têm N=0 e não estão validadas. A matriz inclui
  todas as saídas para não esconder falsos positivos em materiais não coletados.
- Cobertura = aceitos/N; risco seletivo = erros/aceitos; acurácia sobre todos os
  exemplos aceitos/rejeitados é separada da precisão entre aceitos. Com zero aceitos,
  risco é `null`/`n/a`, nunca zero inventado. `unknown` nunca é aceito.
- Falsos positivos por material são contados separadamente no top-1 e nas decisões
  aceitas, inclusive quando um item fora de escopo recebe categoria de material.
  Taxa FP usa o número de referências que **não** são aquele material como denominador.
- Cenário ausente tem N=0 e métricas `null`/`n/a`. Não significa sucesso. Transparência
  não prova material: confrontar erros plástico↔vidro e reflexos no metal.
- Curva usa limiares descritivos fixos (mais o limiar nominal), sem otimização no
  teste. Ela não substitui calibração em validação separada ou análise de risco.
- Tempos são medidos em CPU no executor, incluindo a primeira inferência: carga do
  modelo separada, pipeline (decode/PDI), inferência e total por foto, min/p50/p95/max.
  Preflight/auditoria não entra no tempo por foto. Não extrapolar para celulares.

Relatórios não contêm fotos, nomes de arquivo, IDs de objeto/sessão ou EXIF; usam
índice do manifesto e hashes para rastrear casos localmente. Manifesto/CSV ainda
podem conter nomes privados; manter todos fora do Git. Revisar e autorizar qualquer
relatório antes de publicar (hashes e distribuições também podem ser sensíveis).
Guardar autorizações e auditoria externa em registro privado separado. O relatório
permanece `independent_test=false` mesmo depois de auditado; a aprovação externa deve
ser anexada separadamente, sem editar resultados automaticamente.

## Testes e próximo gate

```bash
python -m pytest tests/test_evaluation_manifest.py tests/test_field_manifest_cli.py tests/test_field_evaluation.py -q
python -m ruff check src scripts tests
python -m pytest -q
python -m pip check
```

Testes criam imagens sintéticas temporárias, conferem métricas calculadas à mão e
exercitam as CLIs. Nenhum resultado desses testes deve ser apresentado como campo.
**Próximo gate:** o grupo fornecer coleta real autorizada, manifesto congelado e
revisão da origem/objetos/sessões. Sem isso, encerrar no suporte automatizável.
