# Evidência de processamento digital de imagens — APS

**Referência de código:** `main` `89622ec714b815c216a9215ab9ba69999b39c6b8`, conferido em 08/11/2026.
Este documento acompanha o Prompt 06. A referência normativa disponível é
[plano_validacao_aps_4_dias.md](plano_validacao_aps_4_dias.md); o PDF do manual
não está neste workspace, e não foi possível conferir diretamente sua edição.
O SHA final e os resultados de CI devem ser consultados no PR desta etapa.

## Situação verificável

O suporte de aquisição, manipulação, filtros, segmentação, morfologia e exportação
é executável e testável. **O resultado acadêmico em fotos reais continua pendente**:
não foram disponibilizadas imagens reais com autorização nesta etapa. Os arquivos
sintéticos de testes técnicos não foram usados para preencher figuras de campo.
Não há medição nova de acurácia de reconhecimento, nem candidato/modelo promovido.

| Evidência necessária | Estado | Resultado/figuras |
| --- | --- | --- |
| Exemplo real autorizado A (sustentabilidade, contexto do objeto) | PENDENTE: foto e declaração de autorização | Não executado em foto real |
| Exemplo real autorizado B (outro objeto/cena) | PENDENTE: foto e declaração de autorização | Não executado em foto real |
| Fracasso diagnosticado em sombra, reflexo ou transparência | PENDENTE: execução e inspeção humana de caso real | Não se afirmou falha a partir de hipótese |
| IoU/Dice em fotos reais | PENDENTE: referência humana revisada, se disponível | Sem referência, não medir nem substituir por área |
| PNG/ZIP/CSV/Markdown/hashes e cálculos | Implementados, verificáveis pelos testes | Fixtures sintéticas somente para validar a engenharia |

## Proposta e implementação

O problema é orientar o descarte de resíduos com informação visual e confirmação
humana. A proposta de visão computacional combina entrada RGB preservada para o
classificador ONNX com um laboratório explícito de PDI. O laboratório permite
investigar como intensidade, ruído, cor, fundo e morfologia afetam a máscara.
Máscara e prévia não estabelecem composição, conteúdo ou limpeza do material.

Os módulos `image_processing/filters.py`, `segmentation/methods.py` e
`segmentation/morphology.py` foram revisados. Nenhum defeito demonstrado exigiu
alterar os algoritmos nesta etapa. A mudança está na evidência e sua apresentação,
não nos pixels preparados para o classificador. A autoria e os backends estão na
[tabela de operações](pratica_processamento_imagens.md#autoria-das-operações).

| Requisito | Código | Evidência por foto |
| --- | --- | --- |
| Aquisição e manipulação | `image_io.py`, `preprocessing.py`, `app/pipeline.py` | RGB orientado, dimensões, hash, cinza/histograma e preparação |
| Filtragem | `filters.py`, seleção do pipeline | Controle/gaussiano/mediana/Sobel, parâmetro e diferença medida |
| Segmentação | `methods.py` | Limiar/polaridade Otsu ou regra HSV/GrabCut, máscara bruta |
| Morfologia | `morphology.py` | Abertura/fechamento, kernel, quatro primitivas e máscara final |
| Regiões/contornos | `elements.py`, gradiente morfológico | Componentes com conectividade 4, caixas/área/centroide e gradiente |
| Proposta de visão computacional | Preparação RGB e contrato do pipeline | Prévia da entrada de inferência independente da máscara, checksum e contrato |
| Resultados reproduzíveis | `processing_evidence.py`, `processing_academic.py`, CLI de exportação | PNG/CSV/Markdown/JSON/ZIP dos mesmos arrays, versões/hashes e tempos reais |

Na baseline consultada, filtros de cor podem afetar a preparação RGB de inferência;
esta etapa não os desacopla nem promete compatibilidade de todas as variantes.
A correção pertence ao [PR #21](https://github.com/Gabrielhamad/ecoscan/pull/21).
O exportador não carrega o encoder e não mede previsão/latência do modelo.

## Protocolo para produzir os resultados reais

1. Fornecer ao menos duas fotos de objetos reais de sustentabilidade autorizadas,
   preferencialmente metal, plástico ou vidro em cenários distintos. Não fotografar
   rostos, documentos ou endereços. Registrar em arquivo privado identificadores de
   objeto/sessão, origem, licença/consentimento, câmera, iluminação e contexto.
2. Incluir um caso difícil real (sombra, metal reflexivo ou plástico/vidro transparente).
   O caso pode integrar os dois exemplos se houver falha efetivamente observada;
   caso contrário, coletar outro. Não criar uma falha fictícia.
3. Congelar o conjunto e seus hashes antes da comparação. Escolher as operações
   e registrar sua hipótese; não retirar da entrega exemplos desfavoráveis.
4. Executar os comandos abaixo com caminhos reais, guardar ambiente e SHA.
5. Inspecionar os relatórios por variante, relacionando cada afirmação à figura.
   Se houver anotação humana, seguir o protocolo de referência da prática e repetir
   em diretório novo. Não ajustar a máscara humana para combinar com a saída.
6. Preencher benefício, erro e limitação de cada operação. Conferir se a suposta
   melhoria remove detalhes do objeto ou une fundo/objetos indevidamente.
7. Guardar os ZIPs em local privado autorizado; levar à apresentação somente as
   fotos consentidas. A ausência de nomes/caminhos no manifesto não anonimiza pixels.

Substituir `/dados/aps/...` por arquivos reais autorizados. Estes são comandos de
coleta futura, **não execuções ou resultados já obtidos**:

```bash
python scripts/export_processing_evidence.py \
  --image /dados/aps/exemplo_a.png --output reports/aps/exemplo_a \
  --source-kind field_photo --consent --compare-filters --segmentation otsu
python scripts/export_processing_evidence.py \
  --image /dados/aps/exemplo_b.png --output reports/aps/exemplo_b \
  --source-kind field_photo --consent --compare-filters --segmentation hsv_color
python scripts/export_processing_evidence.py \
  --image /dados/aps/caso_dificil.png --output reports/aps/caso_dificil \
  --source-kind field_photo --consent --filter median --segmentation grabcut
```

A execução real criará `report.md` na raiz, com links para os relatórios de cada
variante; cada relatório referencia **as figuras que existem naquele pacote**:
`00_original_rgb.png`, cinza/histogramas, `antes_depois.png`, `components.png` e
`contours.png`. As imagens separadas de cada etapa permitem inspeção sem a escala
da prancha. `parameters.csv`, `histogram.csv` e `manifest.json` guardam números
exatos, diferenças, referência opcional, hashes e tempos.

Para cada caso completar, usando as figuras exportadas:

| Campo de análise humana | Preenchimento obrigatório após executar |
| --- | --- |
| Algoritmo/parâmetro | Método solicitado e efetivo, parâmetros CSV, backend e versão |
| Efeito observado | Diferença de pixels/estrutura efetivamente vista, vinculada ao arquivo PNG |
| Benefício e custo | Ruído aparente removido, detalhe perdido ou efeito nulo, sem chamar isso de acurácia |
| Falha diagnosticada | Região incorreta concreta e fator observado; causas não verificadas permanecem hipóteses |
| Resultado | IoU/Dice somente com referência revisada; em sua ausência, descrição qualitativa explícita |
| Limitação | Generalização não demonstrada, dependência de fundo/luz/polaridade/enquadramento |

## Validação e limites

```bash
python -m ruff check src scripts tests
python -m pytest -q
python -m pip check
```

Testes pixel a pixel existentes são preservados. Os testes adicionais em
`tests/test_processing_academic.py` verificam exportação sem perdas, histogramas
exatos, parâmetros, hash de todos os arquivos, ZIP estável para a mesma execução,
IoU/Dice conhecidos, rejeição de referência inadequada, ausência de métricas sem
referência, CLI sem reprocessar ilustrações, consentimento/origem declarados e
preservação da entrada RGB do modelo. A CI do PR registra o resultado real.

Tempos variam entre execuções e não foram atribuídos a primitivas não
instrumentadas. Hash de arquivo PNG não equivale ao hash do array: o manifesto
explica ambos. Alterações de dependência/fonte podem alterar a codificação ou
prancha. Reproduzir no mesmo ambiente e comparar os arrays, além dos arquivos.

A revisão técnica não conclui o gate de campo. Após receber as fotos, gerar e
inspecionar os pacotes reais, substituir os estados pendentes por resultados
medidos e associar o relatório acadêmico final às figuras autorizadas. Não afirmar
precisão nova, sucesso em sustentabilidade ou falha de segmentação sem essa etapa.
