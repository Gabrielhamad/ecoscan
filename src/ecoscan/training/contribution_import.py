"""Import reviewed exports into an isolated source directory, never into test data."""
import hashlib
import io
import json
from pathlib import Path
from uuid import UUID
from zipfile import ZipFile

from PIL import Image


def import_approved(package: Path, destination: Path, classes) -> dict:
    if destination.exists():
        raise ValueError("Use uma pasta nova para preservar os lotes anteriores.")
    accepted, seen = [], {}
    with ZipFile(package) as archive:
        if sum(info.file_size for info in archive.infolist()) > 100 * 1024 * 1024:
            raise ValueError("Pacote excede 100 MB descompactado.")
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("Pacote com entradas duplicadas.")
        records = json.loads(archive.read("manifest.json"))
        if not isinstance(records, list):
            raise ValueError("Manifesto invalido.")
        for row in records:
            if row.get("status") != "approved" or row.get("consent") is not True:
                continue
            category = row.get("expected_class")
            if category not in classes:
                continue
            identifier = str(UUID(row["id"]))
            expected = f"images/{category}/{identifier}.jpg"
            if row.get("image") != expected:
                raise ValueError("Caminho de imagem invalido no manifesto.")
            data = archive.read(expected)
            if len(data) > 1024 * 1024:
                raise ValueError("Imagem excede 1 MB.")
            with Image.open(io.BytesIO(data)) as image:
                if image.format != "JPEG":
                    raise ValueError("Formato de imagem invalido.")
                image.verify()
            digest = hashlib.sha256(data).hexdigest()
            if digest in seen:
                if seen[digest] != category:
                    raise ValueError("Mesma foto aprovada com rotulos conflitantes.")
                continue
            seen[digest] = category
            accepted.append((category, identifier, data, {
                "id": identifier, "revision": row.get("revision", 0),
                "class": category, "file_sha256": digest,
                "source_image_sha256": row.get("image_sha256"),
                "split": "unassigned", "training_status": "not_trained",
            }))
    if not accepted:
        raise ValueError("Nenhuma imagem aprovada e consentida no pacote.")
    destination.mkdir(parents=True)
    for category, identifier, data, record in accepted:
        folder = destination / category
        folder.mkdir(exist_ok=True)
        (folder / f"{identifier}.jpg").write_bytes(data)
    manifest = {"status": "ready_for_dataset_review", "active_model_changed": False,
                "package_sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
                "images": [row[3] for row in accepted]}
    (destination / "import_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
