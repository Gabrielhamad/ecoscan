"""Build a candidate from analyst-approved examples; never replace the active model."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from uuid import uuid4

import numpy as np

from ecoscan.app.pipeline import ProcessingPipelineOptions, run_processing_pipeline
from ecoscan.classification.visual_features import extract_visual_features
from ecoscan.classification.visual_knn import VisualKnnClassifier
from ecoscan.services.learning_contributions import (
    _LOCK, _write, contribution_dir, contribution_image, list_contributions,
)


_TRAINING_LOCK = threading.Lock()
MAX_BATCH = 40


def training_dir(config):
    return config.directories["reports"] / "secretariat_training"


def candidate_runs(config):
    records = {row["id"]: row for row in list_contributions(config)}
    runs = []
    for path in training_dir(config).glob("*/run.json"):
        run = json.loads(path.read_text(encoding="utf-8"))
        if run["status"] == "awaiting_validation":
            for identifier, revision in run.get("contribution_versions", {}).items():
                row = records.get(identifier, {})
                if row.get("status") != "approved" or row.get("revision", 0) != revision:
                    run["status"] = "invalidated_by_review"
                    break
        runs.append(run)
    return sorted(runs, key=lambda row: row["created_at"], reverse=True)


def train_candidate(config, *, reviewer) -> dict:
    if not reviewer.is_admin:
        raise PermissionError("Somente a secretaria pode iniciar um treino.")
    if not _TRAINING_LOCK.acquire(blocking=False):
        raise ValueError("Já existe um treino em execução nesta instância.")
    try:
        return _train(config, reviewer)
    finally:
        _TRAINING_LOCK.release()


def _train(config, reviewer):
    if config.model.get("output_path") and (config.project_root / config.model["output_path"]).is_file():
        raise ValueError("O modelo ativo usa outra arquitetura. Exporte as aprovadas para o pipeline de treino correspondente.")
    approved = [row for row in list_contributions(config)
                if row["status"] == "approved" and row.get("consent")
                and row["expected_class"] in config.classes]
    if not approved:
        raise ValueError("Aprove pelo menos uma foto com rótulo confirmado antes de treinar.")
    unique = {}
    for row in approved:
        previous = unique.get(row["image_sha256"])
        if previous and previous["expected_class"] != row["expected_class"]:
            raise ValueError("Há fotos iguais aprovadas com rótulos diferentes. Revise os protocolos.")
        unique[row["image_sha256"]] = row
    if len(unique) > MAX_BATCH:
        raise ValueError("Mais de 40 fotos aprovadas: exporte o lote para treinamento fora da hospedagem gratuita.")
    base_path = config.directories["models"] / "vision_classifier.npz"
    base_hash = hashlib.sha256(base_path.read_bytes()).hexdigest()
    signature = hashlib.sha256(json.dumps([
        base_hash, sorted((row["id"], row.get("revision", 0), row["expected_class"])
                          for row in approved), config.filters, config.segmentation,
    ], sort_keys=True).encode()).hexdigest()
    for existing in candidate_runs(config):
        if existing.get("signature") == signature and existing["status"] == "awaiting_validation":
            return existing
    identifier = str(uuid4())
    directory = training_dir(config) / identifier
    directory.mkdir(parents=True, exist_ok=True)
    run = {"id": identifier, "created_at": time.time(), "status": "running",
           "signature": signature, "base_sha256": base_hash, "requested_by": reviewer.id,
           "contribution_ids": [row["id"] for row in approved],
           "contribution_versions": {row["id"]: row.get("revision", 0) for row in approved},
           "new_examples": len(unique), "active_model_changed": False}
    _write(directory / "run.json", run)
    try:
        baseline = VisualKnnClassifier.load(base_path)
        raw_base = baseline.features * baseline.feature_std + baseline.feature_mean
        features, labels = [], []
        for row in unique.values():
            result = run_processing_pipeline(contribution_image(config, row), config,
                                             ProcessingPipelineOptions(filter_name="auto", segmentation_name="auto"))
            features.append(extract_visual_features(result.segmentation_result.image, baseline.metadata.feature_config))
            labels.append(row["expected_class"])
        # Refit normalization over old + reviewed examples, retaining legacy rejection classes.
        candidate = VisualKnnClassifier.fit(
            np.vstack([raw_base, np.vstack(features)]), baseline.labels + labels,
            classes=sorted(set(baseline.classes) | set(labels)),
            feature_config=baseline.metadata.feature_config, threshold=baseline.metadata.threshold,
            k_neighbors=baseline.metadata.k_neighbors, distance_metric=baseline.metadata.distance_metric,
            score_mode=baseline.metadata.score_mode,
            notes=["Candidato da secretaria. Sem validacao independente; nao promover automaticamente.",
                   f"Base sha256: {base_hash}", f"Lote: {identifier}"],
        )
        with _LOCK:
            current = {row["id"]: row for row in list_contributions(config)}
            if hashlib.sha256(base_path.read_bytes()).hexdigest() != base_hash:
                raise ValueError("O modelo-base mudou durante o treino. Gere outro candidato.")
            for row in approved:
                latest = current.get(row["id"], {})
                if latest.get("status") != "approved" or latest.get("revision", 0) != row.get("revision", 0):
                    raise ValueError("Uma revisão mudou durante o treino. Gere outro candidato.")
            candidate.save(directory / "candidate.npz")
            run.update(status="awaiting_validation", completed_at=time.time(),
                       candidate_sha256=hashlib.sha256((directory / "candidate.npz").read_bytes()).hexdigest(),
                       validation="Pendente: conjunto independente, precisao/recall por classe e casos de confusao. Nenhuma acuracia nova comprovada.")
            _write(directory / "run.json", run)
            for row in approved:
                row.update(training_status="awaiting_validation", candidate_id=identifier)
                _write(contribution_dir(config) / f"{row['id']}.json", row)
        return run
    except Exception as exc:
        run.update(status="failed", completed_at=time.time(), error_type=type(exc).__name__)
        _write(directory / "run.json", run)
        raise
