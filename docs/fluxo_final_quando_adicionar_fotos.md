# Fluxo final quando o dataset crescer

Este é o caminho recomendado quando novas fotos forem adicionadas.

## 1. Adicionar imagens

Use a aba `Dataset` do app para enviar imagens diretamente para `data/raw/<classe>`, ou importe uma pasta:

```powershell
python scripts\ingest_dataset_folder.py --source-folder C:\caminho\para\fotos --class-id battery
```

Também é possível organizar manualmente em `data/raw/<classe>`:

```text
data/raw/
  plastic/
  paper_cardboard/
  metal/
  glass/
  organic/
  battery/
  electronic/
```

Se quiser criar novas classes, atualize também:

- `config/settings.json`;
- `config/disposal_guidance.json`;
- `config/web_image_sources.json`, se a classe também tiver captura web.

As classes especiais `lamp`, `medicine`, `cooking_oil`, `aerosol` e `chemical_packaging` já estão estruturadas em `config/settings.json` para orientar descarte e receber imagens, mas só devem ser consideradas confiáveis no reconhecimento depois de volume mínimo, curadoria e avaliação.

O manifesto de uploads fica em `reports/dataset_uploads/upload_manifest.csv`.

## 2. Analisar dataset

```powershell
python scripts\analyze_dataset.py --dataset data\raw --output reports\dataset_analysis
python scripts\dataset_readiness.py
```

Verifique:

- quantidade por classe;
- quanto falta para cada classe;
- imagens inválidas;
- resoluções;
- duplicatas;
- grades `class_examples_<classe>.jpg`.

## 3. Criar planilha de revisão

```powershell
python scripts\create_review_sheet.py
```

Edite `reports/dataset_review/review_sheet.csv`:

- `status=accepted` mantém imagem;
- `status=rejected` remove do dataset curado;
- `suggested_class` permite corrigir a classe.

## 4. Aplicar revisão

```powershell
python scripts\apply_review_sheet.py --overwrite
```

As imagens aprovadas vão para `data/curated`.

## 5. Dividir dataset

Para usar as imagens revisadas:

```powershell
python scripts\split_dataset.py --source data\curated --overwrite
```

Para usar direto o dataset bruto:

```powershell
python scripts\split_dataset.py --overwrite
```

## 6. Treinar baseline

```powershell
python scripts\train_baseline.py
python scripts\evaluate_model.py --model models\baseline_classifier.json --split test --output reports\evaluation\baseline_test
```

Para medir o comportamento real do aplicativo, incluindo filtragem, segmentação, modelo e validações visuais:

```powershell
python scripts\evaluate_app_analysis.py --split test --output reports\evaluation\app_analysis_test
```

## 7. Preparar ou treinar modelo final

Gerar plano:

```powershell
python scripts\train_transfer.py
```

Treinar modelo final com TensorFlow:

```powershell
python scripts\train_transfer.py --run
python scripts\evaluate_model.py --model models\ecoscan_transfer.keras --split test --output reports\evaluation\transfer_test
```

Recomendação: usar Python 3.12 para TensorFlow.

## 8. Rodar aplicação

```powershell
python scripts\run_streamlit_app.py
```

O app usa `models/ecoscan_transfer.keras` se existir. Caso contrário, usa `models/baseline_classifier.json`.

## 9. Validar aceite técnico

Antes de apresentar, rode a validação executável dos cenários principais:

```powershell
python scripts\run_acceptance_checks.py
```

O relatório é salvo em `reports/acceptance_checks`.

## 10. Gerar auditoria, status e pacote final

```powershell
python scripts\project_audit.py
python scripts\project_status.py
python scripts\prepare_delivery_pack.py
```

As evidências ficam em:

- `reports/project_audit`;
- `reports/project_status.md`;
- `reports/delivery_pack`.
