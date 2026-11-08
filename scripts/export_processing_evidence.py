"""Export the executed PDI arrays, without running recognition or claiming field accuracy."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, replace
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ecoscan.app.pipeline import run_processing_pipeline
from ecoscan.app.processing_options import ProcessingPipelineOptions, default_processing_options
from ecoscan.config import load_config
from ecoscan.image_processing.filters import FILTERS
from ecoscan.image_processing.validation import validate_image_file
from ecoscan.segmentation.methods import SEGMENTATION_METHODS
from ecoscan.segmentation.morphology import OPERATIONS
from ecoscan.services.processing_academic import load_reference_mask
from ecoscan.services.processing_evidence import evidence_archive, processing_evidence_zip


def _file_sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _checkout_sha() -> str | None:
    result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=PROJECT_ROOT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def _options(args: argparse.Namespace) -> ProcessingPipelineOptions:
    values = asdict(default_processing_options(load_config()))
    if args.options:
        overrides = json.loads(args.options.read_text(encoding='utf-8'))
        if not isinstance(overrides, dict) or set(overrides) - set(values):
            raise ValueError('Options must be an object with ProcessingPipelineOptions fields only')
        values.update(overrides)
    for key in ('filter_name', 'segmentation_name', 'morphology_name'):
        selected = getattr(args, key)
        if selected is not None:
            values[key] = selected
        if not isinstance(values[key], str):
            raise ValueError(f'{key} must be a string')
    choices = (set(FILTERS) | {'auto'}, set(SEGMENTATION_METHODS) | {'auto'}, set(OPERATIONS))
    for key, allowed in zip(('filter_name', 'segmentation_name', 'morphology_name'), choices):
        if values[key] not in allowed:
            raise ValueError(f'Unsupported {key}')
    for key in ('filter_parameters', 'segmentation_parameters', 'morphology_parameters'):
        if values[key] is not None and not isinstance(values[key], dict):
            raise ValueError(f'{key} must be an object or null')
    return ProcessingPipelineOptions(**values)


def _comparison(summaries: list[tuple[str, dict]]) -> dict[str, bytes]:
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer)
    writer.writerow(['variant', 'filter', 'changed_pixels', 'mean_absolute_difference',
                     'max_absolute_difference', 'raw_iou', 'final_iou', 'final_dice',
                     'total_ms', 'classifier_input_sha256'])
    rows = ['# Comparação controlada de PDI', '',
            'Mesma imagem de entrada, mesma segmentação/morfologia solicitadas; apenas o filtro solicitado varia.',
            'Tempos são de uma execução, sem benchmark estatístico. Nenhuma inferência foi executada.',
            'Sem referência humana não se calcula IoU/Dice. Nenhum ranking de qualidade é inferido dos pixels alterados.', '',
            '| Variante | Parâmetros, figuras e limitações | Pixels alterados pelo filtro | Tempo total (ms) |',
            '| --- | --- | --- | --- |']
    for name, manifest in summaries:
        stage = manifest['stages'][1]
        quality = manifest['reference_quality']
        writer.writerow([name, manifest['implementations']['filter']['method'], stage['changed_pixels'],
                         stage['mean_absolute_difference'], stage['max_absolute_difference'],
                         quality['raw']['iou'] if quality else '', quality['final']['iou'] if quality else '',
                         quality['final']['dice'] if quality else '', manifest['timings_ms']['total'],
                         manifest['classifier_input_sha256']])
        rows.append(f"| {name} | [Relatório]({name}/report.md) | {stage['changed_pixels']} | {manifest['timings_ms']['total']} |")
    rows += ['', 'O RGB de reconhecimento exportado é independente da máscara. Nesta baseline, filtros podem alterar o RGB; '
             'os hashes em comparison.csv registram isso. Este experimento não altera o contrato ou a preparação do modelo.',
             'Origem e autorização são declarações do operador, não auditoria externa. '
             'Anotar o efeito real e diagnosticar o fracasso antes de concluir o relatório acadêmico.']
    return {'comparison.csv': buffer.getvalue().encode('utf-8'),
            'report.md': ('\n'.join(rows) + '\n').encode('utf-8')}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New private directory; never overwritten')
    parser.add_argument('--source-kind', choices=['field_photo', 'synthetic_fixture'], required=True)
    parser.add_argument('--consent', action='store_true', help='Operator declares authorization to process/export the image')
    parser.add_argument('--options', type=Path, help='JSON object of ProcessingPipelineOptions overrides')
    parser.add_argument('--filter', dest='filter_name', choices=['auto', *FILTERS])
    parser.add_argument('--segmentation', dest='segmentation_name', choices=['auto', *SEGMENTATION_METHODS])
    parser.add_argument('--morphology', dest='morphology_name', choices=list(OPERATIONS))
    parser.add_argument('--compare-filters', action='store_true', help='Run none, gaussian, median, sobel once each')
    parser.add_argument('--reference-mask', type=Path, help='Human binary PNG at working-mask coordinates; no resizing')
    parser.add_argument('--reference-reviewed', action='store_true', help='Operator attests human review of this annotation')
    args = parser.parse_args(argv)
    if not args.consent:
        parser.error('--consent is required; the ZIP contains the original image')
    if bool(args.reference_mask) != args.reference_reviewed:
        parser.error('--reference-mask and --reference-reviewed must be provided together')
    if args.compare_filters and args.filter_name:
        parser.error('Use either --filter or --compare-filters')
    if args.output.exists():
        parser.error('Output exists; choose a new directory')
    try:
        config = load_config()
        options = _options(args)
        validate_image_file(args.image, allowed_extensions=config.allowed_extensions, min_size=config.min_image_size)
        input_hash = _file_sha256(args.image)
        reference_hash = _file_sha256(args.reference_mask) if args.reference_mask else None
        variants = ['none', 'gaussian', 'median', 'sobel'] if args.compare_filters else [options.filter_name]
        files: dict[str, bytes] = {}
        summaries = []
        for name in variants:
            variant = replace(options, filter_name=name)
            result = run_processing_pipeline(args.image, config, variant)
            reference = load_reference_mask(args.reference_mask, result.segmentation_result.mask.shape) if args.reference_mask else None
            context = {'checkout_sha': _checkout_sha(),
                       'settings_file_sha256': _file_sha256(PROJECT_ROOT / 'config/settings.json'),
                       'export_script_sha256': _file_sha256(Path(__file__)),
                       'options': asdict(variant), 'reference_file_sha256': reference_hash,
                       'reference_human_review_declared': args.reference_reviewed,
                       'inference_executed': False}
            package = processing_evidence_zip(result, reference_mask=reference, input_sha256=input_hash,
                                               source_kind=args.source_kind, consent_recorded=args.consent,
                                               execution_context=context)
            with zipfile.ZipFile(io.BytesIO(package)) as archive:
                prefix = name + '/' if args.compare_filters else ''
                files.update({prefix + entry: archive.read(entry) for entry in archive.namelist()})
                summaries.append((name, json.loads(archive.read('manifest.json'))))
        if _file_sha256(args.image) != input_hash or (args.reference_mask and _file_sha256(args.reference_mask) != reference_hash):
            raise ValueError('Input changed during export; no evidence saved')
        if args.compare_filters:
            files.update(_comparison(summaries))
        # Build once; extracted figures and ZIP are the same bytes, never a second processing.
        package = evidence_archive(files)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.ecoscan-evidence-', dir=args.output.parent) as temporary:
            staged = Path(temporary) / 'package'
            staged.mkdir()
            for name, data in files.items():
                path = staged / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            (staged / 'evidence.zip').write_bytes(package)
            staged.rename(args.output)
    except (ValueError, OSError, TypeError, RuntimeError) as exc:
        parser.error(str(exc))
    print(f'Evidence exported: {len(variants)} execution(s); {args.source_kind}; no recognition metrics')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
