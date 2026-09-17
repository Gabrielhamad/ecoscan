# EcoScan

EcoScan é um guia inteligente de descarte responsável de resíduos, com foco em uso real por celular ou PC.

O sistema recebe a imagem de um resíduo, aplica um pipeline reproduzível de processamento digital de imagens, classifica a categoria visual e retorna orientação de descarte, preparo do material, impacto ambiental e busca de ponto próximo. A documentação técnica mantém a rastreabilidade necessária para a APS de Processamento de Imagens e Visão Computacional.

## Estado atual

Estrutura principal implementada:

- estrutura do projeto;
- configuração centralizada;
- classes iniciais configuráveis;
- captura web rastreável por Wikimedia Commons, Openverse e TACO;
- base de orientações separada do modelo;
- destinos visuais de descarte por classe;
- impactos ambientais do mau descarte;
- experiência visual institucional da Secretaria do Meio Ambiente, com linguagem de portal municipal sem copiar marca oficial;
- perfis locais de usuário e admin para demonstração;
- campanha ambiental com missões, pontos persistentes e recompensas configuráveis;
- denúncia de mau descarte com triagem por imagem e revisão administrativa;
- base local de pontos de coleta filtrável por material;
- plano de fotos por classe para fortalecer o dataset;
- validação básica de imagens;
- filtragem e segmentação adaptativas;
- reconhecimento por baseline com rejeição por baixa confiança;
- câmera via navegador e modo EcoScan Live;
- análise exploratória de dataset;
- ingestão de imagens do grupo para `data/raw`;
- manifesto de uploads e bloqueio de duplicatas exatas;
- preparação automática das imagens para reconhecimento;
- geração de relatórios em `reports/dataset_analysis`;
- testes automatizados com `unittest`;
- documentação acadêmica inicial.

O reconhecimento atual usa uma baseline. O modelo final por transfer learning depende das fotos reais do grupo, curadoria, split e avaliação comparativa.

## Classes configuradas

As classes configuradas em `config/settings.json` são:

- `plastic`
- `paper_cardboard`
- `metal`
- `glass`
- `organic`
- `battery`
- `electronic`
- `lamp`
- `medicine`
- `cooking_oil`
- `aerosol`
- `chemical_packaging`

Oito classes já atingiram o volume bruto mínimo de 50 imagens. `medicine`, `cooking_oil`, `aerosol` e `chemical_packaging` estão estruturadas e possuem base semente, mas ainda precisam de mais captura e curadoria antes de serem tratadas como reconhecimento confiável.

## Estrutura

```text
ecoscan/
  config/
    collection_points.json
  data/
  raw/
    aerosol/
    battery/
    chemical_packaging/
    cooking_oil/
    electronic/
    glass/
    lamp/
    medicine/
    metal/
    organic/
    paper_cardboard/
    plastic/
    processed/
    train/
    validation/
    test/
  docs/
  logs/
  models/
  notebooks/
  reports/
  scripts/
  src/ecoscan/
    app/
    classification/
    disposal/
    image_processing/
    metrics/
    segmentation/
    services/
    ui/
    utils/
  tests/
```

## Instalação

Recomendado para a APS: Python 3.12.

```powershell
cd ecoscan
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Se o alias `python` do Windows Store interferir, use o caminho do Python instalado na máquina ou ajuste o PATH.

## Rodar para PC e celular

Modo recomendado para teste local, celular na mesma rede e apresentacao:

```powershell
cd ecoscan
python scripts\ecoscan_access.py --restart
```

Ou execute o launcher:

```powershell
.\run_ecoscan_rede.ps1
```

O script inicia o app principal e o EcoScan Live, valida as portas e imprime os links corretos para:

- usuario no PC;
- admin no PC;
- usuario no celular ou outro PC da mesma rede;
- camera ao vivo.

Para apenas conferir os links atuais:

```powershell
python scripts\ecoscan_access.py --check-only
```

Importante: o IP da rede pode mudar. Nao use link antigo sem rodar a checagem. A camera ao vivo no celular pode exigir HTTPS por regra do navegador; o upload de imagem funciona em HTTP local. Para uso por qualquer pessoa fora da rede, publique o app em HTTPS. Veja `docs/acesso_multidispositivo.md`.

Para organizar teste remoto com colegas em outros lugares, use `docs/teste_remoto_grupo.md`. Quando o app errar, o formulario "O reconhecimento errou?" salva a imagem e a classe correta em `reports/recognition_feedback`.

## Hospedar gratuito para o grupo

Para uso por colegas em lugares diferentes, o caminho recomendado é publicar o app principal no Streamlit Community Cloud.

Arquivos já preparados:

- `streamlit_app.py`
- `requirements.txt`
- `runtime.txt`
- `.streamlit/config.toml`
- modelos leves liberados em `.gitignore`

Passo curto:

```text
1. Suba o projeto para um repositório GitHub.
2. Entre em https://share.streamlit.io.
3. Crie um app apontando para streamlit_app.py.
4. Compartilhe a URL https://NOME-DO-APP.streamlit.app com o grupo.
```

No gratuito, use upload/câmera do app principal. O EcoScan Live na porta `8765` continua como recurso local ou para uma hospedagem HTTPS dedicada. Veja `docs/hospedagem_gratuita.md`.

Para gerar o checklist:

```powershell
python scripts\check_deployment_ready.py
```

## Preparar dataset

Coloque as imagens em pastas por classe dentro de `data/raw`:

```text
data/raw/
  aerosol/
  plastic/
  paper_cardboard/
  metal/
  glass/
  organic/
  battery/
  electronic/
  lamp/
  medicine/
  cooking_oil/
  chemical_packaging/
```

Formatos aceitos inicialmente: JPG, JPEG e PNG.

## Analisar dataset

```powershell
cd ecoscan
python scripts\analyze_dataset.py --dataset data\raw --output reports\dataset_analysis
python scripts\prepare_dataset_images.py --source data\raw --output data\processed --overwrite
```

O script gera:

- `dataset_analysis.json`
- `class_distribution.csv`
- `resolution_distribution.csv`
- `invalid_images.csv`
- `potential_issues.txt`
- `random_examples.jpg`
- `class_distribution.png`
- `resolution_distribution.png`

## Capturar imagens abertas da web

Para criar ou ampliar uma base semente a partir de imagens abertas com manifesto de licença:

```powershell
cd ecoscan
python scripts\capture_wikimedia_dataset.py --images-per-class 50
python scripts\capture_openverse_dataset.py --images-per-class 50 --classes lamp,medicine,cooking_oil,aerosol,chemical_packaging
python scripts\capture_taco_dataset.py --images-per-class 50 --classes medicine,aerosol
python scripts\analyze_dataset.py --dataset data\raw --output reports\dataset_analysis
```

As capturas geram imagens em `data/raw/<classe>` e manifestos de atribuição em `reports/web_capture`, `reports/openverse_capture` e `reports/taco_capture`.

Essa base serve para desenvolver e demonstrar o pipeline. Para treinamento final, revise visualmente as imagens, remova exemplos fora da classe e considere complementar com datasets maiores documentados em `docs/dataset_web_research.md`.

Depois de capturar imagens, consulte também `docs/dataset_capture_results.md` e as grades `reports/dataset_analysis/class_examples_<classe>.jpg`.

## Testes

Sem instalar `pytest`, os testes podem ser executados com:

```powershell
cd ecoscan
$env:PYTHONPATH="src"
python -m unittest discover -s tests
```

## Próximas fases

Fases 2 e 3 implementadas:

- carregamento de imagem para uso do usuário;
- redimensionamento e normalização;
- filtragem adaptativa com diagnóstico de qualidade e comparação de sequências;
- experimentos com filtros;
- comparação visual lado a lado.
- segmentação modular e adaptativa;
- análise de elementos visuais segmentados;
- experimentos com threshold, HSV, contornos e GrabCut;
- documentação dos efeitos observados.

Scripts úteis:

```powershell
python scripts\run_processing_demo.py --image data\raw\metal\metal_0001_12-ounce-aluminum-soda-can-32167233397.jpg --filter auto --segmentation auto
python scripts\compare_filters.py --image data\raw\metal\metal_0001_12-ounce-aluminum-soda-can-32167233397.jpg
python scripts\compare_segmentation.py --image data\raw\metal\metal_0001_12-ounce-aluminum-soda-can-32167233397.jpg
```

Detalhes técnicos estão em `docs/fase_2_3_processamento.md`.

Fases 4 e 5:

- preparar dataset final;
- criar baseline simples;
- baseline;
- transfer learning;
- treinamento;
- avaliação com accuracy, precision, recall, F1-score e matriz de confusão.

Fase 4 inicial:

```powershell
python scripts\prepare_dataset_images.py --source data\raw --output data\processed --overwrite
python scripts\split_dataset.py --source data\processed --overwrite
python scripts\train_baseline.py
```

Detalhes em `docs/fase_4_baseline.md`.

MVP inicial com baseline:

```powershell
python scripts\run_inference.py --image data\raw\metal\metal_0001_12-ounce-aluminum-soda-can-32167233397.jpg
python scripts\run_streamlit_app.py
```

A interface Streamlit está em `src/ecoscan/ui/streamlit_app.py`. Detalhes em `docs/fase_6_7_mvp_inicial.md`.

Detecção por câmera:

```powershell
python scripts\run_streamlit_app.py
```

Na aba `Análise`, selecione `Câmera`, capture uma foto e o sistema executa filtro, segmentação, análise de elementos e reconhecimento.

Reconhecimento ao vivo com câmera traseira do celular:

```powershell
python scripts\ecoscan_access.py --restart
```

Abra a URL exibida pelo terminal no celular. A página `EcoScan Live` prioriza a câmera traseira (`facingMode: environment`), envia frames ao backend local e desenha caixas com IDs estáveis sobre os elementos segmentados. Em celular, o navegador pode exigir HTTPS para liberar câmera fora de `localhost`; nesse caso, use um túnel seguro, publique em HTTPS ou informe `--cert-file` e `--key-file` ao servidor live.

Com OpenCV instalado, também existe captura direta por script:

```powershell
python scripts\capture_webcam.py --camera-index 0
```

## Adicionar fotos do grupo

Pelo app, use a aba `Dataset` para enviar várias imagens a uma classe ativa. Os arquivos ficam em `data/raw/<classe>` e o manifesto fica em `reports/dataset_uploads/upload_manifest.csv`.

Por script:

```powershell
python scripts\ingest_dataset_folder.py --source-folder C:\caminho\para\fotos --class-id battery
```

O fluxo completo para expandir classes e treinar novamente está em `docs/gestao_dataset_e_classes.md`.

## Fluxo final do projeto

Quando você adicionar mais fotos:

```powershell
python scripts\analyze_dataset.py --dataset data\raw --output reports\dataset_analysis
python scripts\dataset_readiness.py
python scripts\create_review_sheet.py
python scripts\apply_review_sheet.py --overwrite
python scripts\prepare_dataset_images.py --source data\curated --output data\processed --overwrite
python scripts\split_dataset.py --source data\processed --overwrite
python scripts\train_baseline.py
python scripts\evaluate_model.py --model models\baseline_classifier.json --split test --output reports\evaluation\baseline_test
python scripts\train_transfer.py
python scripts\train_transfer.py --run
python scripts\evaluate_model.py --model models\ecoscan_transfer.keras --split test --output reports\evaluation\transfer_test
python scripts\run_acceptance_checks.py
python scripts\project_status.py
python scripts\project_audit.py
python scripts\generate_academic_report.py
python scripts\prepare_delivery_pack.py
python scripts\run_streamlit_app.py
```

Documentos de referência:

- `docs/fluxo_final_quando_adicionar_fotos.md`
- `docs/gestao_dataset_e_classes.md`
- `docs/pipeline_profissional_filtragem_reconhecimento.md`
- `docs/arquitetura_final.md`
- `docs/checklist_aps.md`
- `docs/roadmap_profissional.md`
- `docs/plano_execucao_em_grande_escala.md`
- `docs/live_camera_mobile.md`
- `reports/delivery_pack/indice_entrega.md`
