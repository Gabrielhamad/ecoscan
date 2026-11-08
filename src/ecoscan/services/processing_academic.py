"""Academic evidence derived from executed arrays; never infer segmentation quality."""
from __future__ import annotations

import csv
import hashlib
from importlib.metadata import PackageNotFoundError, version
import io
import json
from pathlib import Path
import platform
from typing import TYPE_CHECKING, Any
import zlib

import numpy as np
from PIL import Image, ImageDraw

from ecoscan.image_processing.preprocessing import to_grayscale
from ecoscan.image_processing.validation import validate_image_file
from ecoscan.services.processing_evidence import _png, array_digest

if TYPE_CHECKING:
    from ecoscan.app.pipeline import ProcessingPipelineResult


def processing_code_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parents[1]
    paths = [path for folder in ('image_processing', 'segmentation', 'app')
             for path in (root / folder).glob('*.py')]
    paths += [Path(__file__), root / 'services/processing_evidence.py']
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def _runtime_versions() -> dict[str, str]:
    result = {'python': platform.python_version(), 'zlib': zlib.ZLIB_RUNTIME_VERSION}
    for name in ('numpy', 'Pillow', 'opencv-python-headless'):
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = 'not installed under this distribution name'
    return result


def load_reference_mask(path: Path, shape: tuple[int, int]) -> np.ndarray:
    info = validate_image_file(path, allowed_extensions={'.png'}, min_size=(1, 1))
    with Image.open(path) as image:
        if info.format != 'PNG' or image.mode not in {'1', 'L'} or image.getexif().get(274, 1) != 1:
            raise ValueError('Reference must be an oriented binary PNG (L or 1)')
        mask = np.asarray(image)
        if mask.dtype == bool:
            mask = mask.astype(np.uint8) * 255
        _check_mask(mask, shape)
        return mask.copy()


def _check_mask(mask: np.ndarray, shape: tuple[int, int]) -> None:
    if len(shape) != 2 or mask.shape != shape or mask.dtype != np.uint8 or not np.isin(mask, [0, 255]).all():
        raise ValueError('Reference must match the working mask exactly, uint8 with values 0/255; no resizing')


def segmentation_metrics(prediction: np.ndarray, reference: np.ndarray) -> dict[str, Any]:
    _check_mask(reference, prediction.shape)
    _check_mask(prediction, reference.shape)
    predicted, expected = prediction > 0, reference > 0
    intersection = int(np.count_nonzero(predicted & expected))
    union = int(np.count_nonzero(predicted | expected))
    size = int(np.count_nonzero(predicted)) + int(np.count_nonzero(expected))
    return {'intersection': intersection, 'union': union,
            'iou': intersection / union if union else 1.0,
            'dice': 2 * intersection / size if size else 1.0,
            'empty_convention': 'two empty masks = 1; this does not establish a correct object annotation'}


def _histogram_png(counts: np.ndarray) -> bytes:
    image = Image.new('RGB', (560, 300), 'white')
    draw = ImageDraw.Draw(image)
    draw.text((12, 8), 'Histograma: intensidade 0-255; contagem exata no CSV', fill='black')
    peak = max(1, int(counts.max()))
    for index, value in enumerate(counts):
        height = round(220 * int(value) / peak)
        draw.rectangle((24 + 2 * index, 260 - height, 25 + 2 * index, 260), fill='#27755c')
    draw.text((24, 274), '0', fill='black')
    draw.text((515, 274), '255', fill='black')
    draw.text((24, 28), f'Pico: {int(counts.max())} pixels (escala vertical linear)', fill='black')
    return _png(np.asarray(image))


def _csv(header: list[str], rows: list[list[Any]]) -> bytes:
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().encode('utf-8')


def academic_files(pipeline: ProcessingPipelineResult, manifest: dict[str, Any],
                   reference_mask: np.ndarray | None = None) -> dict[str, bytes]:
    if pipeline.raw_segmentation_result is None or pipeline.morphology_result is None:
        raise ValueError('Reprocess this image to export the academic evidence with morphology')
    before = to_grayscale(pipeline.preprocessing.resized)
    after = to_grayscale(pipeline.filter_result.image)
    hist_before, hist_after = (np.bincount(gray.ravel(), minlength=256) for gray in (before, after))
    artifacts = {'00_original_rgb.png': _png(pipeline.loaded.array),
                 'intensity_before.png': _png(before), 'intensity_after.png': _png(after),
                 'histogram_before.png': _histogram_png(hist_before), 'histogram_after.png': _histogram_png(hist_after),
                 'histogram.csv': _csv(['intensity', 'before_count', 'after_count'],
                                        [[i, int(hist_before[i]), int(hist_after[i])] for i in range(256)]),
                 'mask_raw.png': _png(pipeline.raw_segmentation_result.mask),
                 'mask_final.png': _png(pipeline.segmentation_result.mask),
                 'recognition_rgb.png': _png(pipeline.recognition_image),
                 'components.png': _png(pipeline.element_overlay),
                 'contours.png': _png(pipeline.morphology_result.gradient)}
    quality = None
    if reference_mask is not None:
        quality = {'reference_sha256': array_digest(reference_mask),
                   'annotation_origin': 'supplied reference; human annotation correctness is not verified by code',
                   'raw': segmentation_metrics(pipeline.raw_segmentation_result.mask, reference_mask),
                   'final': segmentation_metrics(pipeline.segmentation_result.mask, reference_mask)}
        artifacts['reference_mask.png'] = _png(reference_mask)
    manifest['reference_quality'] = quality
    manifest['acquisition'] = {'encoded_mode': pipeline.loaded.info.mode, 'encoded_format': pipeline.loaded.info.format,
                               'encoded_dimensions': [pipeline.loaded.info.width, pipeline.loaded.info.height],
                               'oriented_rgb_shape': list(pipeline.loaded.array.shape),
                               'oriented_rgb_sha256': array_digest(pipeline.loaded.array),
                               'original_png': 'decoded/oriented RGB; not the original encoded file or EXIF metadata'}
    manifest['diagnostic_representations'] = {
        'grayscale': 'uint8 floor(0.299 R + 0.587 G + 0.114 B); diagnostic only',
        'histogram': 'exact pixel counts, 256 bins, 0..255; not model confidence',
        'before_sha256': array_digest(before), 'after_sha256': array_digest(after)}
    manifest['timings_ms'] = pipeline.metadata.get('timings_ms', {})
    manifest['timing_scope'] = 'Measured pipeline phases, not per primitive; no timings invented for uninstrumented operations'
    manifest['processing_contract'] = pipeline.metadata['recognition_preparation']['contract']
    manifest['implementations'] = {
        'filter': {'method': pipeline.filter_result.name, 'dependency': pipeline.filter_result.dependency,
                   'explanation': pipeline.filter_result.explanation},
        'segmentation': {'method': pipeline.raw_segmentation_result.name, 'dependency': pipeline.raw_segmentation_result.dependency,
                         'explanation': pipeline.raw_segmentation_result.explanation},
        'morphology': 'project implementation using NumPy binary neighborhoods; not cv2.morphologyEx',
        'acquisition_export': 'Pillow decoding, EXIF/RGB conversion and PNG encoding; project validation/orchestration',
        'components': 'project breadth-first traversal with deque/NumPy, 4-neighbor connectivity; Pillow overlay',
        'contours': 'project NumPy morphological gradient: dilation minus erosion of the final mask'}
    manifest['runtime_versions'] = _runtime_versions()
    manifest['source_code_sha256'] = processing_code_hashes()
    manifest['components'] = pipeline.element_analysis.to_dict()
    parameter_rows = []
    for stage in manifest['stages']:
        for key, value in stage['parameters'].items():
            parameter_rows.append([stage['id'], key, json.dumps(value, ensure_ascii=False, sort_keys=True)])
    artifacts['parameters.csv'] = _csv(['stage', 'parameter', 'value_json'], parameter_rows)
    rows = ['# Relatório de processamento para a APS', '',
            f"Origem declarada: **{manifest.get('source_kind', 'not_attested')}**. Autorização: {manifest.get('consent_recorded', False)}.",
            'Este pacote contém a imagem. Compartilhar somente se autorizado. Não mede reconhecimento ou acurácia.', '',
            '## Figuras da execução', '',
            '![Original RGB orientado](00_original_rgb.png)',
            '![Cinza antes do filtro](intensity_before.png)', '![Histograma antes](histogram_before.png)',
            '![Cinza após filtro](intensity_after.png)', '![Histograma após](histogram_after.png)',
            '![Filtro RGB ou resposta de bordas](02_filter_after.png)',
            '![Máscara bruta](mask_raw.png)', '![Máscara final](mask_final.png)',
            '![Prancha das operações executadas](antes_depois.png)',
            '![Componentes](components.png)', '![Contorno morfológico diagnóstico](contours.png)', '',
            '![RGB para inferência, sem máscara](recognition_rgb.png)', '',
            '## Algoritmo, parâmetros e efeito medido', '',
            '| Etapa | Parâmetros efetivos | Efeito medido |', '| --- | --- | --- |']
    for stage in manifest['stages']:
        parameters = json.dumps(stage['parameters'], ensure_ascii=False, sort_keys=True).replace('|', '\\|')
        effect = stage['status']
        if stage['mean_absolute_difference'] is not None:
            effect += f"; diferença média {stage['mean_absolute_difference']:.6f}, máxima {stage['max_absolute_difference']}"
        rows.append(f"| {stage['label']} | {parameters} | {effect} |")
    rows += ['', 'Matriz completa: parameters.csv. Hashes de conteúdo/arquivos/código, contrato e tempos: manifest.json.',
             'Diferença média/máxima: sobre o mapa de diferenças absolutas (máximo entre canais RGB), escala 0–255; não mede qualidade.',
             'Tempo medido por fase: ' + json.dumps(manifest['timings_ms'], sort_keys=True), '',
             '## Referência de segmentação', '',
             ('IoU/Dice contra máscara fornecida: ' + json.dumps(quality, sort_keys=True)) if quality else
             'Não fornecida. IoU/Dice não medidos; pixels alterados/área/componentes não provam qualidade.', '',
             '![Referência fornecida](reference_mask.png)' if quality else '', '',
             '## Implementação e dependências', '', '```json',
             json.dumps(manifest['implementations'], ensure_ascii=False, indent=2), '```', '',
             '## Interpretação e limitações', '',
             'Filtro: ' + pipeline.filter_result.explanation,
             'Segmentação: ' + pipeline.raw_segmentation_result.explanation,
             'Sobel descreve bordas, não uma máscara preenchida. Histogramas não são confiança.',
             'Sombra, reflexo, fundo e transparência podem levar a máscaras erradas. Esta execução não demonstra automaticamente esses fracassos.',
             'A máscara não é aplicada ao RGB de inferência. O RGB exportado é a saída real do pipeline, não uma nova inferência.',
             'No main desta baseline filtros podem alterar esse RGB; comparar seu hash/contrato, sem alegar preparação homologada para todos os controles.',
             'Não foram reexecutadas transformações para ilustrar resultados; cinza e histograma são representações diagnósticas dos arrays existentes.', '',
             '## Análise humana pendente', '',
             'Registrar benefício observado, falha concreta, iluminação/fundo, consentimento e relação com sustentabilidade.',
             'Não chamar redução de ruído aparente de ganho de acurácia sem medições independentes.']
    artifacts['report.md'] = ('\n'.join(rows) + '\n').encode('utf-8')
    return artifacts
