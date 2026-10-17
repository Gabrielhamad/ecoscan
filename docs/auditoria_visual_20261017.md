# Auditoria visual e roteiro de reconhecimento

## Revisao dos dados

Foram inspecionadas dez pranchas com os 433 exemplos de treino. Validacao e
teste nao foram exportados para essa revisao. Casos selecionados tambem foram
abertos em resolucao original. A triagem confirmou fotos inadequadas para
aprender o objeto: logos, retratos, infograficos, codigo, uma placa de pedra,
cenas sem o material visivel e um copo com liquido rotulado como eletronico.

As [25 decisoes registradas](curation_20261017.json) retiram do ajuste 9 exemplos
de pilhas, 3 de eletronicos, 10 de papel/papelao e 3 de metal. Duas exclusoes
de metal sao ilustracoes tecnicas, fora do dominio fotografico; nao foram
declaradas semanticamente incorretas. Exemplos validos amassados, fragmentados,
pequenos ou em fundos complexos foram preservados. Composicao incerta nao
foi relabelada por aparencia. A triagem nao certifica todos os rotulos.

O indice vincula ID, caminho, classe e SHA-256. O aplicador exige indice
inalterado e imagem de treino com hash e classe correspondentes. Nao permite
excluir imagens da validacao ou teste. Originais permanecem intactos; o
manifesto registra `eligible_for_fit`, com 408 imagens elegiveis para ajuste.
O fine-tuning tambem respeita esse campo. Manifestos antigos seguem compativeis.

## Treinamento executado

Tres regularizacoes de regressao logistica e tres de SVM calibrada foram
comparadas pela validacao. A referencia sem revisao foi calculada para
comparacao, mas ficou inelegivel como candidato curado: nao se reintroduzem
exemplos inadequados so para melhorar uma metrica.

| Medida | Referencia anterior | Candidato curado |
| --- | ---: | ---: |
| Macro-F1 na validacao | 67,34% | 66,45% |
| Acerto geral no teste exploratorio | 64,83% | 58,62% |
| Macro-F1 no teste exploratorio | 65,98% | 59,33% |
| Cobertura de respostas aceitas | 31,72% | 0% |

Venceu SVM calibrada, C=1. O fallback de limiar 0,95 rejeitou todas as respostas.
Nas tres fotos reais conhecidas, acertou apenas a hipotese da lata vermelha;
PET e lata alta foram confundidos com vidro, sem aceitacao automatica.
As fotos conhecidas nao entraram no treino nem escolheram parametros.

A revisao corrigiu exemplos comprovadamente inadequados, mas nao demonstrou
ganho de reconhecimento. Nenhum modelo publico foi trocado. O teste reutilizado
e exploratorio. Os rotulos de validacao/teste nao foram auditados nesta rodada;
nao se presume que estejam incorretos nem se excluem seus erros para subir medidas.

## Experimento de localizacao

Foi testado um recorte conservador usando a regiao segmentada mais dominante,
dimensoes minimas e margem. Preserva RGB, sem substituir pixels pela mascara.
Propostas vazias, ambiguas ou quase integrais retornam a imagem completa.
Esse mecanismo e uma proposta por contraste, nao um detector semantico.

Nos casos conhecidos, preservou a imagem completa de PET, propoe um recorte
da lata vermelha e rejeita a proposta ambigua da lata alta. Nao houve evidencia
de melhora nas hipoteses ImageNet. O recorte nao foi incorporado ao treinamento
nem ao aplicativo; ele permanece um diagnostico reproduzivel.

ImageNet1K nao possui categoria especifica de lata de bebida nessa lista.
Uma hipotese generica de garrafa nao comprova, sozinha, falha das caracteristicas
para reconhecer metal. Esses nomes nao sao usados como destinos de descarte.

## Proximas etapas

1. Definir anotacoes verificadas de objeto e material, com criterio para fotos
   sem alvo, varios materiais e composicao incerta.
2. Criar novo lote de aceite separado por objeto/sessao, cobrindo seis classes,
   variacoes reais e casos fora do escopo.
3. Anotar caixas ou mascaras em cenas reais e treinar localizacao. Comparar
   foto completa e recorte sem confiar automaticamente em GrabCut.
4. Reavaliar classificacao/fine-tuning, medindo acerto por material, erros
   aceitos, cobertura, regressoes e tempo de resposta.
5. Integrar um candidato somente quando houver ganho demonstrado nesses criterios.

## Reproducao

```powershell
python scripts/build_dataset_review.py --source ../ecoscan/data/curated --manifest reports/training_embedding_20261016/dataset_manifest.json --output reports/review_20261017
python scripts/train_deep_candidate.py --source ../ecoscan/data/curated --backbone tmp/mobilenetv2-12.onnx --output reports/training_curated_20261017 --feature-cache reports/training_embedding_20261016 --fixed-split reports/training_embedding_20261016/dataset_manifest.json --heads compare --review-index reports/review_20261017/review_index.csv --review-decisions docs/curation_20261017.json
```

Escolher diretorios novos ao repetir rodadas. Pranchas, indice e modelos ficam
locais em `reports/`, ignorados pelo Git. Decisoes, scripts e roteiro estao no
repositorio. `inspect_backbone_cases.py --foreground` executa o diagnostico de
recorte no ambiente opcional TorchVision; a inferencia do backbone usa OpenCV.
