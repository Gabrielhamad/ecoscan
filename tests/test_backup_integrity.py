import json

import pytest

from ecoscan.services.backup_integrity import BUCKETS, seal_backup, verify_backup


@pytest.fixture
def backup(tmp_path):
    (tmp_path / "database.sql").write_text("-- synthetic fixture only", encoding="utf-8")
    for bucket in BUCKETS:
        (tmp_path / "storage" / bucket).mkdir(parents=True)
    return tmp_path


def test_seal_and_verify_empty_buckets(backup):
    assert seal_backup(backup, "a" * 40) == 1
    assert verify_backup(backup) == 1
    with pytest.raises(FileExistsError):
        seal_backup(backup, "b" * 40)


@pytest.mark.parametrize("change", ["missing", "changed", "extra"])
def test_detects_photo_changes(backup, change):
    photo = backup / "storage" / BUCKETS[0] / "example.jpg"
    photo.write_bytes(b"synthetic image")
    seal_backup(backup, "a" * 40)
    if change == "missing":
        photo.unlink()
    elif change == "changed":
        photo.write_bytes(b"different image")
    else:
        (backup / "unexpected.txt").write_text("extra")
    with pytest.raises(ValueError, match="Integridade"):
        verify_backup(backup)


@pytest.mark.parametrize("missing", ["database.sql", "storage/ecoscan-civic-evidence"])
def test_requires_database_and_both_buckets(backup, missing):
    path = backup / missing
    path.rmdir() if path.is_dir() else path.unlink()
    with pytest.raises(ValueError):
        seal_backup(backup, "a" * 40)


def test_rejects_empty_database(backup):
    (backup / "database.sql").write_bytes(b"")
    with pytest.raises(ValueError):
        seal_backup(backup, "a" * 40)


def test_rejects_bad_revision(backup):
    with pytest.raises(ValueError):
        seal_backup(backup, "main")


def test_does_not_follow_manifest_paths(backup):
    seal_backup(backup, "a" * 40)
    manifest = backup / "integrity.json"
    data = json.loads(manifest.read_text())
    data["files"] = {"../../secret": {"bytes": 1, "sha256": "abc"}}
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        verify_backup(backup)


def test_rejects_symlinks(backup):
    link = backup / "link.sql"
    try:
        link.symlink_to(backup / "database.sql")
    except OSError:
        pytest.skip("Symlink creation unavailable on this host")
    with pytest.raises(ValueError, match="Links"):
        seal_backup(backup, "a" * 40)
