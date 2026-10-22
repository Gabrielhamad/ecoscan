import hashlib
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("stage_training_experiment",
    Path(__file__).resolve().parents[1] / "scripts" / "stage_training_experiment.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def inputs(tmp_path):
    roots = [tmp_path / "reference", tmp_path / "extra"]
    rows = []
    for index, root in enumerate(roots):
        root.mkdir()
        path = root / f"photo{index}.jpg"
        path.write_bytes(str(index).encode())
        rows.append({"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "group": "scene", "split": "train", "eligible_for_fit": True,
                     "review_method": "visual", "item_id": "pet_bottle"})
    return roots, rows


def test_staging_preserves_source_and_records_groups(tmp_path):
    roots, rows = inputs(tmp_path)
    output = tmp_path / "output"
    module.stage([rows[0]], roots[0], [rows[1]], roots[1], output)
    assert (roots[0] / rows[0]["path"]).read_bytes() == b"0"
    assert (output / "images" / rows[1]["path"]).read_bytes() == b"1"
    assert "addition:scene" in (output / "groups.csv").read_text()


@pytest.mark.parametrize("change", [{"split": "test"}, {"eligible_for_fit": False},
                                   {"sha256": "changed"}, {"path": "../escape.jpg"},
                                   {"group": None}, {"review_method": ""}])
def test_staging_rejects_invalid_additions_before_writing(tmp_path, change):
    roots, rows = inputs(tmp_path)
    output = tmp_path / "output"
    with pytest.raises(ValueError):
        module.stage([rows[0]], roots[0], [dict(rows[1], **change)], roots[1], output)
    assert not output.exists()
