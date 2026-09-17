# Gestão de dataset e expansão de classes

Este documento define como o grupo deve alimentar o EcoScan sem comprometer as métricas do projeto.

## Objetivo

O EcoScan deve evoluir de um classificador acadêmico de resíduos para um detector de descarte responsável. O escopo ativo inclui recicláveis comuns, orgânicos e resíduos especiais de maior risco ambiental:

- `plastic`;
- `paper_cardboard`;
- `metal`;
- `glass`;
- `organic`;
- `battery`;
- `electronic`;
- `lamp`;
- `medicine`;
- `cooking_oil`;
- `aerosol`;
- `chemical_packaging`.

As sete primeiras classes já atingiram o volume bruto mínimo de 50 imagens na captura web inicial. As classes especiais novas foram ativadas estruturalmente para upload, orientação ambiental e coleta de dados, mas ainda não devem ser tratadas como reconhecimento confiável até completarem volume, curadoria e avaliação.

## Fluxo profissional

1. Coletar imagens por classe, com foco em um resíduo principal por foto.
2. Enviar pelo app ou importar por script para `data/raw/<classe>`.
3. Conferir o manifesto em `reports/dataset_uploads/upload_manifest.csv`.
4. Rodar análise exploratória.
5. Gerar planilha de revisão.
6. Corrigir rótulos e rejeitar imagens ruins.
7. Aplicar curadoria para `data/curated`.
8. Criar novo split de treino, validação e teste.
9. Treinar baseline e modelo final.
10. Avaliar com métricas e matriz de confusão.
11. Rodar validação de aceite e pacote de entrega.

## Regras de coleta

- Priorizar fotos próprias do grupo ou imagens com fonte/licença documentável.
- Quando usar web, preferir fontes abertas com manifesto de atribuição, como `scripts/capture_wikimedia_dataset.py` e `scripts/capture_openverse_dataset.py`.
- Usar fundo simples, boa iluminação e objeto centralizado.
- Evitar várias categorias na mesma foto durante o MVP.
- Variar marcas, tamanhos, ângulos e estados do objeto.
- Não fotografar pessoas, documentos, endereços ou informações pessoais.
- Manter resíduos perigosos fechados e sem manuseio inseguro.

## Critério para considerar uma classe confiável

Recomendação mínima para promover uma classe a reconhecimento confiável:

- pelo menos 50 imagens úteis por classe no MVP;
- idealmente 100 ou mais por classe para treinamento final;
- variedade visual suficiente para não aprender apenas uma marca ou cenário;
- orientação de descarte revisada pelo grupo;
- exemplos aprovados na curadoria.

Se uma classe tiver poucas imagens, ela pode aparecer no app para orientação e coleta, mas o resultado de reconhecimento deve ser tratado como preliminar. Isso evita que o modelo gere uma falsa sensação de confiança.

## Upload pelo app

A aba `Dataset` salva imagens em `data/raw/<classe>` e registra:

- data do upload;
- classe de destino;
- nome original;
- caminho salvo;
- hash SHA-256;
- dimensão;
- status: `saved`, `duplicate` ou `rejected`.

O app bloqueia duplicatas exatas por hash e rejeita extensões ou imagens inválidas. Ele não treina o modelo automaticamente.

## Captura web rastreável

Fontes automatizadas disponíveis:

```powershell
python scripts\capture_wikimedia_dataset.py --images-per-class 50
python scripts\capture_openverse_dataset.py --images-per-class 50 --classes lamp,medicine,cooking_oil,aerosol,chemical_packaging
```

Esses scripts salvam manifestos em:

- `reports/web_capture/wikimedia_capture_manifest.csv`;
- `reports/openverse_capture/openverse_capture_manifest.csv`.

Arquivos com origem ruim ou sem rastreabilidade devem ser movidos para `data/quarantine` e não usados no treinamento final.

## Importação por pasta

Quando o grupo trouxer muitas fotos em uma pasta:

```powershell
python scripts\ingest_dataset_folder.py --source-folder C:\caminho\para\fotos --class-id battery
```

Com subpastas:

```powershell
python scripts\ingest_dataset_folder.py --source-folder C:\caminho\para\fotos --class-id electronic --recursive
```

Depois da importação:

```powershell
python scripts\analyze_dataset.py --dataset data\raw --output reports\dataset_analysis
python scripts\create_review_sheet.py
python scripts\apply_review_sheet.py --overwrite
python scripts\split_dataset.py --source data\curated --overwrite
python scripts\run_acceptance_checks.py
```

## Como adicionar uma classe

Para ativar uma classe nova:

1. Criar ou confirmar a orientação em `config/disposal_guidance.json`.
2. Adicionar o identificador em `config/settings.json`, no campo `classes`.
3. Criar imagens em `data/raw/<nova_classe>`.
4. Rodar análise, curadoria, split e treinamento novamente.

Não basta criar a pasta. O identificador também precisa existir na configuração para o sistema considerar a classe como oficial.
