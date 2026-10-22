import hashlib

from PIL import Image
import pytest

from ecoscan.training.corpus import build_corpus


def sample(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    path = source / "image.png"
    Image.new("RGB", (12, 12), "red").save(path)
    row = {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
           "class_id": "plastic", "item_id": "pet_bottle", "group": "scene-1",
           "split": "train", "review_method": "visual", "eligible_for_fit": True}
    return source, row


def test_build_reports_shortfall_and_preserves_test(tmp_path):
    source, row = sample(tmp_path)
    report = build_corpus([row, dict(row, split="test")], source, tmp_path / "out", ["plastic", "metal"])
    assert report["ready"] is False
    assert report["counts"]["train"]["plastic"] == 1
    assert report["missing_to_minimum"]["validation"]["plastic"] == 20
    assert report["excluded"] == 1


@pytest.mark.parametrize("change", [{"sha256": "wrong"}, {"path": "../other.png"},
                                  {"review_method": ""}, {"group": ""}, {"split": "unknown"}])
def test_invalid_input_leaves_no_output(tmp_path, change):
    source, row = sample(tmp_path)
    with pytest.raises(ValueError):
        build_corpus([dict(row, **change)], source, tmp_path / "out", ["plastic"])
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("split", ["train", "validation"])
def test_rejects_duplicates_and_cross_split_groups(tmp_path, split):
    source, row = sample(tmp_path)
    with pytest.raises(ValueError):
        build_corpus([row, dict(row, split=split)], source, tmp_path / "out", ["plastic"])


def test_never_overwrites_previous_batch(tmp_path):
    source, row = sample(tmp_path)
    output = tmp_path / "out"
    output.mkdir()
    with pytest.raises(ValueError):
        build_corpus([row], source, output, ["plastic"])
