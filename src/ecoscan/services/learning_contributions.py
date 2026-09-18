from __future__ import annotations

import hashlib
import io
import json
import threading
import time
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
from PIL import Image

from ecoscan.services.recognition_feedback import append_recognition_feedback, feedback_dir_from_config
from ecoscan.services.recognition_scope import ITEMS


_LOCK = threading.RLock()
MAX_CONTRIBUTIONS = 200


def contribution_dir(config):
    return feedback_dir_from_config(config) / "contributions"


def _write(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def list_contributions(config) -> list[dict]:
    records = []
    with _LOCK:
        for path in sorted(contribution_dir(config).glob("*.json")):
            records.append(json.loads(path.read_text(encoding="utf-8")))
    return sorted(records, key=lambda row: row["created_at"], reverse=True)


def submit_contribution(config, result, *, item_id: str, reporter_id: str,
                        consent: bool, note: str = "") -> dict:
    if not consent:
        raise ValueError("Autorize o uso da foto para enviar a contribuição.")
    if item_id not in ITEMS:
        raise ValueError("Escolha um item da lista.")
    expected = ITEMS[item_id][1]
    if expected not in (*config.classes, "unknown", "out_of_scope"):
        raise ValueError("Categoria indisponível nesta versão.")
    if len(note) > 600:
        raise ValueError("Use até 600 caracteres na observação.")
    pixels = np.ascontiguousarray(result.pipeline.loaded.array)
    digest = hashlib.sha256(str(pixels.shape).encode() + pixels.tobytes()).hexdigest()
    with _LOCK:
        records = list_contributions(config)
        for record in records:
            if record["reporter_id"] == reporter_id and record["image_sha256"] == digest:
                return record
        if len(records) >= MAX_CONTRIBUTIONS:
            raise ValueError("A fila está cheia. O grupo precisa exportar e revisar as contribuições antes de novos envios.")
        if any(row["reporter_id"] == reporter_id and time.time() - row["created_at"] < 15 for row in records):
            raise ValueError("Aguarde alguns segundos antes de enviar outra contribuição.")
        image = Image.fromarray(pixels)
        image.thumbnail((1280, 1280))
        # Re-encoding pixels drops EXIF, GPS and the original filename.
        pipeline = SimpleNamespace(loaded=SimpleNamespace(array=np.asarray(image)),
                                   filter_result=result.pipeline.filter_result,
                                   segmentation_result=result.pipeline.segmentation_result)
        clean_result = SimpleNamespace(**{key: getattr(result, key) for key in (
            "predicted_class", "top_class", "probability", "accepted", "model_type")}, pipeline=pipeline)
        feedback = append_recognition_feedback(
            config, clean_result, expected_class=expected, reporter_id=reporter_id,
            reporter_name="", source_kind="contribution", note=note,
        )
        record = {
            "id": feedback.id, "created_at": time.time(), "reporter_id": reporter_id,
            "item_id": item_id, "expected_class": expected, "status": "pending",
            "consent": True, "consent_version": "1", "image_sha256": digest,
            "model_sha256": getattr(result, "model_sha256", "unavailable"),
            "feedback": asdict(feedback),
        }
        _write(contribution_dir(config) / f"{feedback.id}.json", record)
        return record


def review_contribution(config, contribution_id: str, *, decision: str, reviewer,
                        item_id: str | None = None, response: str = "",
                        expected_revision: int | None = None) -> dict:
    if not reviewer.is_admin:
        raise PermissionError("A revisão exige uma conta administrativa.")
    if decision not in ("approved", "rejected"):
        raise ValueError("Decisão inválida.")
    identifier = str(UUID(contribution_id))
    if len(response) > 600:
        raise ValueError("Use até 600 caracteres na resposta.")
    with _LOCK:
        path = contribution_dir(config) / f"{identifier}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        previous_candidate = record.get("candidate_id")
        if expected_revision is not None and record.get("revision", 0) != expected_revision:
            raise ValueError("Outro analista atualizou este protocolo. Atualize a fila antes de decidir.")
        if item_id is not None:
            if item_id not in ITEMS:
                raise ValueError("Item revisado inválido.")
            record.setdefault("original_item_id", record["item_id"])
            record["item_id"] = item_id
            record["expected_class"] = ITEMS[item_id][1]
            record["feedback"]["expected_class"] = record["expected_class"]
        if decision == "approved" and record["expected_class"] not in config.classes:
            raise ValueError("Itens fora do escopo ou desconhecidos não entram no treino de categorias.")
        record.update(status=decision, reviewed_by=reviewer.id, reviewed_at=time.time(),
                      response=response.strip(), revision=record.get("revision", 0) + 1,
                      training_status="queued" if decision == "approved" else "excluded")
        record.pop("candidate_id", None)
        record.setdefault("review_history", []).append({
            "decision": decision, "reviewer": reviewer.id, "at": record["reviewed_at"],
            "item_id": record["item_id"], "response": record["response"],
        })
        _write(path, record)
        if previous_candidate:
            for related in list_contributions(config):
                if related["id"] != identifier and related.get("candidate_id") == previous_candidate:
                    related.pop("candidate_id", None)
                    related["training_status"] = "queued" if related["status"] == "approved" else "excluded"
                    _write(contribution_dir(config) / f"{related['id']}.json", related)
        return record


def contribution_image(config, record: dict) -> Path:
    root = (feedback_dir_from_config(config) / "images").resolve()
    path = Path(record["feedback"]["image_path"]).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Foto da contribuição indisponível.")
    return path


def citizen_contributions(config, reporter_id: str) -> list[dict]:
    """Only expose the caller's protocols, without internal paths or analyst IDs."""
    return [{key: row.get(key) for key in (
        "id", "created_at", "status", "item_id", "response", "training_status", "candidate_id")}
        for row in list_contributions(config) if row["reporter_id"] == reporter_id]


def contribution_package(config, records: list[dict], *, approved_only: bool = False) -> bytes:
    output = io.BytesIO()
    manifest = []
    seen_hashes = set()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for record in records:
            if approved_only and (record["status"] != "approved" or record["expected_class"] not in config.classes):
                continue
            if record["image_sha256"] in seen_hashes:
                continue
            seen_hashes.add(record["image_sha256"])
            identifier = str(UUID(record["id"]))
            category = record["expected_class"]
            if category not in (*config.classes, "unknown", "out_of_scope"):
                continue
            filename = f"images/{category}/{identifier}.jpg"
            archive.write(contribution_image(config, record), filename)
            metadata = {key: value for key, value in record.items() if key not in ("reporter_id", "reviewed_by", "review_history", "feedback")}
            metadata["feedback"] = {key: value for key, value in record["feedback"].items()
                                    if key not in ("image_path", "reporter_id", "reporter_name")}
            metadata["image"] = filename
            manifest.append(metadata)
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("README.txt", "Contribuicoes EcoScan. Revisar rotulos antes do treino.\n"
                         "Separar imagens por origem/objeto entre treino, validacao e teste.\n"
                         "Este pacote nao altera o modelo publicado automaticamente.\n")
    return output.getvalue()
