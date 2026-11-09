# Índice verificável das evidências APS

Código congelado: `89622ec714b815c216a9215ab9ba69999b39c6b8`. Data de revisão: 08/11/2026 (America/Sao_Paulo).

Cada link aponta para um arquivo/linha do SHA completo. Os hashes de 48 arquivos estão em [evidencias.json](evidencias.json); o gerador os confere antes de exportar. Status de teste automatizado não é aceite de campo.

| ID | Requisito | Código/documento no SHA | Teste ou referência no SHA | Estado e limite |
| --- | --- | --- | --- | --- |
| APS-01 | Problema, sustentabilidade e proposta | [config/education.json:3](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/config/education.json#L3) | [docs/plano_validacao_aps_4_dias.md:10](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/docs/plano_validacao_aps_4_dias.md#L10) | `implemented_documented` — Revisão acadêmica; não mede impacto ambiental. |
| APS-02 | Aquisição, RGB, EXIF e limites | [src/ecoscan/image_processing/image_io.py:18](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/image_processing/image_io.py#L18) | [tests/test_image_processing.py:59](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/tests/test_image_processing.py#L59) | `automated_evidence` — Câmera física e dispositivos reais: manual_pending. |
| APS-03 | Manipulação e letterbox | [src/ecoscan/image_processing/preprocessing.py:55](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/image_processing/preprocessing.py#L55) | [tests/test_image_processing.py:39](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/tests/test_image_processing.py#L39) | `automated_evidence` — Preserva proporções; verificar a mesma foto autorizada no PC. |
| APS-04 | Filtragem e autoria dos algoritmos | [src/ecoscan/image_processing/filters.py:58](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/image_processing/filters.py#L58) | [tests/test_gaussian_evidence.py:6](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/tests/test_gaussian_evidence.py#L6) | `automated_evidence` — OpenCV/Pillow executam Gaussian/mediana; Sobel usa rotina NumPy do projeto. |
| APS-05 | Segmentação Otsu/HSV/GrabCut | [src/ecoscan/segmentation/methods.py:55](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/segmentation/methods.py#L55) | [tests/test_segmentation.py:11](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/tests/test_segmentation.py#L11) | `automated_evidence` — A máscara não prova material; transparentes/reflexos exigem comparação real. |
| APS-06 | Morfologia e bordas | [src/ecoscan/segmentation/morphology.py:48](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/segmentation/morphology.py#L48) | [tests/test_morphology.py:91](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/tests/test_morphology.py#L91) | `automated_evidence` — Rotina NumPy com fundo zero; sem máscara humana, IoU/Dice não medidos. |
| APS-07 | Componentes e evidência do mesmo processamento | [src/ecoscan/services/processing_evidence.py:158](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/services/processing_evidence.py#L158) | [tests/test_processing_evidence.py:91](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/tests/test_processing_evidence.py#L91) | `automated_evidence` — Componentes e mapa de calor não são detecção supervisionada nem confiança. |
| APS-08 | Modelo ONNX, classes, normalização e hashes | [src/ecoscan/classification/semantic_onnx.py:73](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/classification/semantic_onnx.py#L73) | [tests/test_current_recognition.py:70](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/tests/test_current_recognition.py#L70) | `automated_evidence` — Encoder congelado; métricas independentes por classe ainda ausentes. |
| APS-09 | Confirmação humana e orientação | [src/ecoscan/services/analysis_service.py:89](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/services/analysis_service.py#L89) | [tests/test_current_recognition.py:20](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/tests/test_current_recognition.py#L20) | `automated_evidence` — Aceitação do artefato não é decisão automática do produto. |
| APS-10 | Banco, RLS e privilégios | [migrations/003_community.sql:43](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/migrations/003_community.sql#L43) | [tests/community_database_checks.sql:35](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/tests/community_database_checks.sql#L35) | `ci_fixture_evidence` — PostgreSQL 16 isolado; contas/Supabase de produção: manual_pending. |
| APS-11 | Identidade e autorização no servidor | [src/ecoscan/services/password_identity.py:108](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/services/password_identity.py#L108) | [tests/test_identity.py:22](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/tests/test_identity.py#L22) | `automated_evidence` — service_role exige controle de dono/papel no servidor; não é RLS por usuário direto. |
| APS-12 | Metodologia e CI por SHA | [.github/workflows/quality.yml:17](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/.github/workflows/quality.yml#L17) | [tests/test_community_store.py:181](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/tests/test_community_store.py#L181) | `ci_fixture_evidence` — CI não aprova dispositivos, campo ou restauração em produção. |
| APS-13 | Comparações de fotos reais e caso de falha | [docs/preparation_evidence/default.json:3](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/docs/preparation_evidence/default.json#L3) | [docs/datasets/taco_v1/README.md:14](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/docs/datasets/taco_v1/README.md#L14) | `manual_pending` — Histórico com recortes TACO; faltam originais autorizados e revisão individual de direitos. |
| APS-14 | Métricas medidas e limitações | [docs/model_evaluation/semantic_v1_historical.json:4](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/docs/model_evaluation/semantic_v1_historical.json#L4) | [tests/test_model_evidence.py:12](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/tests/test_model_evidence.py#L12) | `historical_only` — 145 vetores históricos reutilizados; independent_test=false. |
| APS-15 | Bibliografia verificável | [docs/autoria_aps.md:18](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/docs/autoria_aps.md#L18) | [docs/modelo_reconhecimento.md:28](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/docs/modelo_reconhecimento.md#L28) | `document_review` — Fontes primárias registradas em fontes_verificadas.json; manual 2026 não acessível. |
| APS-16 | Apêndice do código congelado | [streamlit_app.py:12](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/streamlit_app.py#L12) | [tests/test_pipeline.py:14](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/tests/test_pipeline.py#L14) | `source_available` — Apêndice textual + exportação de fonte por Git SHA; não inclui modelos, contas ou fotos. |
| APS-17 | Ficha APS e identificação | [docs/autoria_aps.md:8](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/docs/autoria_aps.md#L8) | [docs/plano_validacao_aps_4_dias.md:7](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/docs/plano_validacao_aps_4_dias.md#L7) | `manual_pending` — Ficha preparatória, não modelo oficial; nomes/RAs/horas ficam para cópia privada. |
| APS-18 | Seminário e demonstração 10–15 min | [docs/plano_validacao_aps_4_dias.md:45](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/docs/plano_validacao_aps_4_dias.md#L45) | [docs/roteiro_testes_manuais.md:1](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/docs/roteiro_testes_manuais.md#L1) | `manual_pending` — Roteiro de 13 minutos; ensaios, fotos e PC real ainda pendentes. |

## Execuções e evidências separadas

- Baseline local: Ruff, 496 testes + 108 subtestes e pip check passaram. Reprodução histórica atual: 101/145 top-1, 51 aceitos pelo artefato, 47 corretos, 4 errados e 94 rejeitados; não independente.
- [CI da fonte oficial](https://github.com/Gabrielhamad/ecoscan/actions/runs/42513163053): success, incluindo PostgreSQL 16 isolado. QA-09/QA-18..QA-21 permanecem pendentes de evidência externa.
- TrashNet: JSON/manifesto versionados e teste de consistência; fotos não foram reexecutadas nesta etapa. PDI TACO: resultados históricos consultados, originais e revisão de licença individual pendentes.
- O PR deste pacote registra testes do gerador e formatação; seus resultados não são atribuídos ao código congelado. Não se declarou teste do site/contas/telefones/PC da apresentação.

## Desenvolvimento fora do SHA congelado

Os seguintes PRs foram consultados abertos e não integrados à fonte descrita. Não são evidência de funcionalidades publicadas.

| PR | Assunto | Uso nesta base |
| --- | --- | --- |
| [#20](https://github.com/Gabrielhamad/ecoscan/pull/20) | Auditoria | Contexto e pendência; não integrado |
| [#21](https://github.com/Gabrielhamad/ecoscan/pull/21) | Separação de filtro didático e entrada oficial | Contexto e pendência; não integrado |
| [#22](https://github.com/Gabrielhamad/ecoscan/pull/22) | Dataset/benchmark de campo | Contexto e pendência; não integrado |
| [#23](https://github.com/Gabrielhamad/ecoscan/pull/23) | Candidatos offline | Contexto e pendência; não integrado |
| [#24](https://github.com/Gabrielhamad/ecoscan/pull/24) | Motor de decisão | Contexto e pendência; não integrado |
| [#25](https://github.com/Gabrielhamad/ecoscan/pull/25) | Evidência PDI | Contexto e pendência; não integrado |
| [#26](https://github.com/Gabrielhamad/ecoscan/pull/26) | UX e privacidade | Contexto e pendência; não integrado |
| [#27](https://github.com/Gabrielhamad/ecoscan/pull/27) | Gates CI/locks | Contexto e pendência; não integrado |
| [#28](https://github.com/Gabrielhamad/ecoscan/pull/28) | Aceite publicado | Contexto e pendência; não integrado |
| [#29](https://github.com/Gabrielhamad/ecoscan/pull/29) | Pacote executável APS | Contexto e pendência; não integrado |

## Comandos de reprodução

```bash
python -m ruff check src scripts tests
python -m pytest -q
python -m pip check
python scripts/evaluate_bundled_model.py --output reports/aps_report/reproducao_historica.json
python scripts/generate_academic_report.py --output reports/aps_report/relatorio_aps.md --docx --code-appendix
```

Os comandos de relatório rodam no branch deste pacote; o texto descreve exclusivamente o SHA congelado. DOCX requer Pandoc de desenvolvimento, fora do runtime web. Falta de fonte Arial, manual, fotos ou hardware continua explicitamente pendente; não é conversão de evidência em aprovação.

## Gate acadêmico que continua aberto

| Dependência | Estado | Quem deve fornecer/verificar |
| --- | --- | --- |
| Manual/ficha oficial 2026 | `not_available` | Professora/grupo: confirmar versão, modelo e regras de submissão |
| Nomes, RAs, horas e contribuições | `private_fill_pending` | Integrantes reais, em cópia privada |
| Duas fotos autorizadas e fracasso diagnosticado F01–F03 | `not_provided` | Grupo: origem/direitos, parâmetros, resultados e figuras |
| Máscara humana/IoU/Dice | `not_provided` | Anotar e medir somente se referência correspondente existir |
| Conjunto novo independente/calibração | `not_provided` | Coleta por objeto/sessão; nenhuma promoção por conveniência |
| PC/telefone e três ensaios de 10–15 min | `manual_pending` | Grupo: data, SHA, duração real e ocorrências |
| Arial no aparelho e paginação final | `manual_pending` | Abrir DOCX com Arial legítima e conferir antes de submeter |
| Aceite do SHA e release | `not_approved` | Grupo/mantenedor após correções, CI e evidência externa |

## Apêndice textual: trechos exatos da fonte

### load_rgb_image

Fonte: [src/ecoscan/image_processing/image_io.py:18](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/image_processing/image_io.py#L18). Método/integração conforme atribuição no relatório.

```python
def load_rgb_image(
    path: str | Path,
    *,
    allowed_extensions: set[str] | frozenset[str],
    min_size: tuple[int, int],
) -> LoadedImage:
    info = validate_image_file(
        path,
        allowed_extensions=allowed_extensions,
        min_size=min_size,
    )
    with Image.open(info.path) as image:
        image = ImageOps.exif_transpose(image)
        if "A" in image.getbands() or "transparency" in image.info:
            rgba = image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            rgb = Image.alpha_composite(background, rgba).convert("RGB")
        else:
            rgb = image.convert("RGB")
        array = np.asarray(rgb, dtype=np.uint8)
    return LoadedImage(info=info, array=array)
```

### _otsu_threshold

Fonte: [src/ecoscan/segmentation/methods.py:55](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/segmentation/methods.py#L55). Método/integração conforme atribuição no relatório.

```python
def _otsu_threshold(gray: np.ndarray) -> int:
    histogram = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    total = gray.size
    sum_total = np.dot(np.arange(256), histogram)

    sum_background = 0.0
    weight_background = 0.0
    best_variance = -1.0
    threshold = 0

    for level in range(256):
        weight_background += histogram[level]
        if weight_background == 0:
            continue
        weight_foreground = total - weight_background
        if weight_foreground == 0:
            break

        sum_background += level * histogram[level]
        mean_background = sum_background / weight_background
        mean_foreground = (sum_total - sum_background) / weight_foreground
        variance = weight_background * weight_foreground * (mean_background - mean_foreground) ** 2
        if variance > best_variance:
            best_variance = variance
            threshold = level
    return threshold
```

### image_features

Fonte: [src/ecoscan/classification/semantic_onnx.py:73](https://github.com/Gabrielhamad/ecoscan/blob/89622ec714b815c216a9215ab9ba69999b39c6b8/src/ecoscan/classification/semantic_onnx.py#L73). Método/integração conforme atribuição no relatório.

```python
def image_features(self, rgb):
        if rgb.shape != (224, 224, 3) or rgb.dtype != np.uint8:
            raise ValueError("Expected prepared RGB image")
        image = rgb.astype(np.float32) / 255.0
        image = (image - np.array([.48145466, .4578275, .40821073], dtype=np.float32)) / np.array(
            [.26862954, .26130258, .27577711], dtype=np.float32)
        with self.lock:
            feature = self.session.run(None, {"image": image.transpose(2, 0, 1)[None]})[0][0]
        return feature
```
