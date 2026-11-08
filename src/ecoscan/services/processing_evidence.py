"""Lossless evidence from arrays produced by the actual analysis, without rerunning filters."""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from ecoscan.app.pipeline import ProcessingPipelineResult


def array_digest(array: np.ndarray) -> str:
    header = json.dumps({"shape": list(array.shape), "dtype": str(array.dtype)}, sort_keys=True)
    return hashlib.sha256(header.encode("utf-8") + b"\0" + array.tobytes(order="C")).hexdigest()


@dataclass(frozen=True)
class ProcessingEvidence:
    key: str
    label: str
    before: np.ndarray
    after: np.ndarray
    parameters: dict[str, Any]
    applied: bool = True

    @property
    def difference(self) -> np.ndarray | None:
        if self.before.shape != self.after.shape:
            return None
        delta = np.abs(self.after.astype(np.int16) - self.before.astype(np.int16))
        return (delta.max(axis=2) if delta.ndim == 3 else delta).astype(np.uint8)

    @property
    def changed_pixels(self) -> int | None:
        difference = self.difference
        return None if difference is None else int(np.count_nonzero(difference))

    @property
    def status(self) -> str:
        if not self.applied:
            return "Controle: operação desativada"
        if self.changed_pixels == 0:
            return "Executada, sem alteração de pixels"
        if self.changed_pixels is None:
            return "Executada; dimensões ou representação diferentes"
        return f"Executada: {self.changed_pixels} pixels alterados"

    def manifest(self) -> dict[str, Any]:
        difference = self.difference
        return {
            "id": self.key, "label": self.label, "applied": self.applied,
            "status": self.status, "parameters": self.parameters,
            "changed_pixels": self.changed_pixels,
            "mean_absolute_difference": float(difference.mean()) if difference is not None else None,
            "max_absolute_difference": int(difference.max()) if difference is not None else None,
            "before": {"shape": list(self.before.shape), "dtype": str(self.before.dtype),
                       "sha256": array_digest(self.before)},
            "after": {"shape": list(self.after.shape), "dtype": str(self.after.dtype),
                      "sha256": array_digest(self.after)},
        }


def processing_evidence(pipeline) -> tuple[ProcessingEvidence, ...]:
    raw = pipeline.raw_segmentation_result
    morphology = pipeline.morphology_result
    if raw is None or morphology is None:
        return ()
    stages = [
        ProcessingEvidence("01_resize", "Preparação: redimensionamento",
                           pipeline.loaded.array, pipeline.preprocessing.resized,
                           {"resampling": "area", "target_size": pipeline.preprocessing.metadata["target_size"],
                            "aspect_ratio": "preserved; no upscaling",
                            "input": "RGB, orientação EXIF já corrigida"}),
        ProcessingEvidence("02_filter", "Filtro: " + pipeline.filter_result.name,
                           pipeline.preprocessing.resized, pipeline.filter_result.image,
                           pipeline.filter_result.parameters,
                           pipeline.filter_result.parameters.get("sequence", [pipeline.filter_result.name]) != ["none"]),
        ProcessingEvidence("03_segmentation", "Segmentação: " + raw.name,
                           pipeline.filter_result.image, raw.mask, raw.parameters, raw.name != "none"),
    ]
    before = raw.mask
    for index, (name, after) in enumerate(morphology.stages, start=1):
        label = {"erosion": "Erosão", "dilation": "Dilatação"}[name]
        stages.append(ProcessingEvidence(
            f"04_morphology_{index:02d}_{name}", f"Morfologia {index}: {label}", before, after,
            {key: morphology.metadata[key] for key in
             ("operation", "kernel_size", "kernel_shape", "kernel", "anchor", "iterations", "border")} |
            {"primitive": name}))
        before = after
    if not morphology.stages:
        stages.append(ProcessingEvidence("04_morphology_control", "Morfologia: controle",
                                         raw.mask, morphology.mask, {"operation": "none"}, False))
    stages.append(ProcessingEvidence(
        "05_mask_preview", "Máscara: visualização auxiliar",
        pipeline.filter_result.image, pipeline.segmentation_result.image,
        {"background_rgb": [255, 255, 255],
         "mask_sha256": array_digest(pipeline.segmentation_result.mask),
         "destination": "inspeção; não enviada ao classificador"},
        raw.name != "none" or morphology.metadata["operation"] != "none"))
    stages.append(ProcessingEvidence(
        "06_classifier_input", "Entrada RGB do classificador",
        (pipeline.preprocessing.resized if pipeline.filter_result.name in {"sobel", "canny"}
         else pipeline.filter_result.image), pipeline.recognition_image,
        pipeline.metadata["recognition_preparation"], True))
    return tuple(stages)


def _png(array: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(array).save(buffer, format="PNG")
    return buffer.getvalue()


def evidence_manifest(pipeline) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "source": "arrays da execução; nenhuma transformação é refeita para ilustrar",
        "digest": "SHA-256 de JSON shape/dtype (sort_keys=True), byte NUL e bytes C-order",
        "difference": "máxima diferença absoluta entre canais, escala 0–255 sem amplificação",
        "scope": "Aquisição RGB até a imagem entregue ao classificador; não mede acurácia.",
        "classifier_input_sha256": array_digest(pipeline.recognition_image),
        "stages": [stage.manifest() for stage in processing_evidence(pipeline)],
    }


def evidence_overview(pipeline) -> bytes:
    """A row for each actual stage; image scale is fixed within each pair."""
    stages = processing_evidence(pipeline)
    cell_width, row_height = 320, 300
    canvas = Image.new("RGB", (cell_width * 3, 72 + row_height * len(stages)), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 15)
        title_font = ImageFont.truetype("arial.ttf", 21)
    except OSError:
        font = title_font = ImageFont.load_default()
    draw.text((16, 10), "EcoScan | Antes e depois da execução", fill="black", font=title_font)
    for column, label in enumerate(("Antes", "Depois", "Diferença absoluta (0–255)")):
        draw.text((column * cell_width + 16, 42), label, fill="black", font=font)
    for row, stage in enumerate(stages):
        y = 72 + row * row_height
        draw.text((12, y), stage.label + " — " + stage.status, fill="black", font=font)
        dimensions = [stage.before.shape[:2], stage.after.shape[:2]]
        scale = min(296 / max(w for h, w in dimensions), 244 / max(h for h, w in dimensions))
        for column, array in enumerate((stage.before, stage.after, stage.difference)):
            if array is None:
                draw.text((column * cell_width + 15, y + 90), "Não comparável pixel a pixel", fill="black", font=font)
                continue
            image = Image.fromarray(array).convert("RGB")
            # Nearest neighbor for all previews avoids inventing intermediate mask levels.
            image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))),
                                 Image.Resampling.NEAREST)
            canvas.paste(image, (column * cell_width + (cell_width - image.width) // 2, y + 35))
        draw.line((0, y + row_height - 1, canvas.width, y + row_height - 1), fill="#d1d5db")
    return _png(np.asarray(canvas))


def processing_evidence_zip(pipeline: ProcessingPipelineResult, *, reference_mask: np.ndarray | None = None,
                            input_sha256: str | None = None, source_kind: str = 'not_attested',
                            consent_recorded: bool = False,
                            execution_context: dict[str, Any] | None = None) -> bytes:
    """Private, per-analysis package in memory; never includes server paths or account data."""
    from ecoscan.services.processing_academic import academic_files
    manifest = evidence_manifest(pipeline)
    manifest.update(schema_version=3, input_file_sha256=input_sha256, source_kind=source_kind,
                    consent_recorded=consent_recorded, execution_context=execution_context)
    artifacts = {'antes_depois.png': evidence_overview(pipeline)}
    for stage in processing_evidence(pipeline):
        artifacts[stage.key + '_before.png'] = _png(stage.before)
        artifacts[stage.key + '_after.png'] = _png(stage.after)
        if stage.difference is not None:
            artifacts[stage.key + '_difference.png'] = _png(stage.difference)
    artifacts.update(academic_files(pipeline, manifest, reference_mask))
    manifest['files_sha256'] = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(artifacts.items())}
    artifacts['manifest.json'] = json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False).encode('utf-8')
    return evidence_archive(artifacts)


def evidence_archive(artifacts: dict[str, bytes]) -> bytes:
    """Stable container for the same captured execution, including its measured timings."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name, data in sorted(artifacts.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o600 << 16
            archive.writestr(entry, data)
    return buffer.getvalue()
