# Avanco do reconhecimento - 17/10/2026

## Problema e mecanismo

Recortar as tres fotos conhecidas com caixas manuais nao resolveu a
classificacao do candidato MobileNet: foto completa, uma hipotese correta;
recortes, nenhuma. O recorte continuou experimental e nao foi ativado.

Foi avaliada outra representacao visual: CLIP ViT-B/32 QuickGELU, usando
OpenCLIP e pesos pre-treinados originais. E um Vision Transformer, nao uma
rede convolucional. A preparacao de imagem permanece antes da rede:
orientacao, RGB, proporcoes, filtros adaptativos e letterbox 224x224. O
transform nativo adiciona tensor e normalizacao CLIP; nao aplica a normalizacao
ImageNet da MobileNet. Segmentacao continua como diagnostico independente.

O banco fixo de descricoes cobre as seis categorias e uma categoria auxiliar
`unknown`. Descricoes sao comparadas com a imagem por similaridade. Esses
escores relativos nao sao probabilidades garantidas de descarte correto.
Nao ha geracao de respostas por uma API paga ou envio das fotos para um modelo remoto.

## Experimentos e escolha

Primeiro foi avaliado o modo zero-shot, sem ajustar parametros com exemplos
do EcoScan. Ele acertou as tres fotos conhecidas, mas teve apenas 59,31% de
acerto no teste completo; sozinho, nao superou a referencia.

Depois foram extraidas caracteristicas CLIP dos 408 exemplos de treino
revisados e das fotos reservadas. Somente os 408 exemplos ajustaram a regressao
logistica; as 25 exclusoes visuais foram respeitadas. Foram comparadas tres
regularizacoes e pesos semanticos fixos de 0, 50% e 75%, alem do zero-shot.

A validacao escolheu C=0,1 e mistura de 50% entre o classificador supervisionado
e as descricoes. Macro-F1 de validacao: 72,49%. O limiar 0,7 foi escolhido na
validacao, com 68 acertos em 74 respostas aceitas (91,89%). As fotos reais
conhecidas foram avaliadas depois e nao escolheram parametros.

## Resultado exploratorio

| Medida no mesmo teste | MobileNet anterior | CLIP hibrido |
| --- | ---: | ---: |
| Acerto geral | 64,83% (94/145) | 73,79% (107/145) |
| Macro-F1 nas seis classes | 65,98% | 73,73% |
| Respostas aceitas | 46/145 | 70/145 |
| Acerto entre aceitas | 91,30% (42/46) | 92,86% (65/70) |
| Erros aceitos | 4 | 5 |

Houve ganho de 8,96 pontos percentuais de acerto geral. A cobertura aumentou,
mas cinco respostas erradas ainda foram aceitas. As outras 75 imagens foram
rejeitadas. Nao apresentar 92,86% como acerto em todas as imagens.

| Material | F1 anterior | F1 CLIP hibrido |
| --- | ---: | ---: |
| Pilhas | 77,42% | 68,97% |
| Eletronicos | 75,86% | 76,92% |
| Vidro | 55,56% | 70,18% |
| Metal | 75,36% | 80,00% |
| Papel/papelao | 60,71% | 78,57% |
| Plastico | 50,98% | 67,74% |

Pilhas regrediram e precisam de investigacao e novas amostras verificadas.
Nao houve melhoria uniforme em todos os materiais. O macro-F1 informado
considera as seis classes conhecidas, de forma comparavel com a referencia;
respostas `unknown` para materiais conhecidos contam como erros.

## Fotos reais conhecidas e recarga

| Foto | Resultado do candidato hibrido |
| --- | --- |
| Garrafas PET | Plastico, escore relativo 0,895, aceita |
| Lata vermelha | Metal, escore relativo 0,775, aceita |
| Lata alta de energetico | Metal, escore relativo 0,904, aceita |

O bundle salvo foi recarregado e repetiu os tres acertos, sem refazer o treino.
O carregador verifica o hash do modelo antes de desserializar, alem de preparo,
classes, descricoes e arquitetura. Joblib deve ser carregado apenas de artefatos
locais confiaveis produzidos pela equipe.

As fotos conhecidas nao entraram no ajuste supervisionado, mas nao formam um
teste cego. O teste de 145 fotos foi reutilizado em varias comparacoes e tambem
e exploratorio. Possivel sobreposicao com o pre-treinamento amplo nao pode ser
excluida. Ainda falta avaliacao independente de negativos e itens fora do escopo.

## Uso e hospedagem

O candidato esta disponivel para inferencia local por comando. O aplicativo
publico ainda nao foi alterado: e necessario validar pilhas, casos fora do
escopo, memoria e tempo total no ambiente de hospedagem. O checkpoint local
tem aproximadamente 605 MB; nao foi acrescentado as dependencias do Streamlit.
A mediana de 0,178 s medida no modo zero-shot refere-se somente a inferencia
do encoder em CPU local com quatro threads, excluindo preparo e carregamento.
Isso nao comprova desempenho de camera ao vivo.

Nao ha localizacao automatica ou rastreamento novos nesta etapa. As anotacoes
de objetos e a exportacao COCO estao descritas no [guia de anotacoes](anotacoes_objetos.md).

## Reproduzir

Usar o ambiente isolado de treinamento, com PyTorch CPU e TorchVision ja
instalados. Instalar `open_clip_torch==3.3.0` somente nesse ambiente.
Versoes usadas: PyTorch 2.14.1+cpu e TorchVision 0.29.1+cpu.

```powershell
tmp/finetune-env/Scripts/python.exe -m pip install open_clip_torch==3.3.0
tmp/finetune-env/Scripts/python.exe scripts/train_contrastive_probe.py --source ../ecoscan/data/curated --reference-run reports/training_curated_20261017 --cache-dir tmp/clip-weights --output reports/contrastive_probe_20261017 --cases tmp/recognition_cases.csv
tmp/finetune-env/Scripts/python.exe scripts/evaluate_recognition_cases.py --candidate reports/contrastive_probe_20261017 --cases tmp/recognition_cases.csv --cache-dir tmp/clip-weights --output reports/contrastive_probe_20261017/reloaded_cases.json
```

Usar novas saidas em repeticoes. O CSV de casos tem `path,expected_class`.
O cache baixa pesos publicos; nao exige chave de API. Os pesos utilizados
`open_clip_model.safetensors` tiveram SHA-256
`e6d1bd7789aa45192b3bf90570a789b478bae1b74ebcce7eddd908e83a2b7c31`.
Fotos, caracteristicas, pesos e bundles ficam locais em diretorios ignorados
pelo Git. Codigo, metodo e resultados estao documentados para o grupo.

Fontes: [OpenCLIP](https://github.com/mlfoundations/open_clip),
[licenca OpenCLIP](https://github.com/mlfoundations/open_clip/blob/main/LICENSE),
[CLIP e limites do modelo](https://github.com/openai/CLIP/blob/main/model-card.md).
