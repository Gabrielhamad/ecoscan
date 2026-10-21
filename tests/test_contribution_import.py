import io
import json
from uuid import uuid4
from zipfile import ZipFile

import pytest
from PIL import Image

from ecoscan.training.contribution_import import import_approved


def package(tmp_path, consent=True, status="approved", unsafe=False):
    identifier = str(uuid4())
    data = io.BytesIO()
    Image.new("RGB", (32, 32), "red").save(data, format="JPEG")
    name = f"images/plastic/{identifier}.jpg"
    path = tmp_path / "package.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr(name, data.getvalue())
        archive.writestr("manifest.json", json.dumps([{
            "id": identifier, "expected_class": "plastic", "consent": consent,
            "status": status, "image": "../escape.jpg" if unsafe else name,
        }]))
    return path


def test_import_is_isolated_and_not_marked_trained(tmp_path):
    output = tmp_path / "batch"
    result = import_approved(package(tmp_path), output, ["plastic"])
    assert result["active_model_changed"] is False
    assert result["images"][0]["training_status"] == "not_trained"
    assert len(list(output.rglob("*.jpg"))) == 1
    with pytest.raises(ValueError):
        import_approved(tmp_path / "package.zip", output, ["plastic"])


@pytest.mark.parametrize("kwargs", [{"consent": False}, {"status": "pending"}, {"unsafe": True}])
def test_invalid_package_does_not_create_batch(tmp_path, kwargs):
    output = tmp_path / "batch"
    with pytest.raises(ValueError):
        import_approved(package(tmp_path, **kwargs), output, ["plastic"])
    assert not output.exists()
