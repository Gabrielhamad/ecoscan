"""Academic evidence integrity is separate from field/model/official acceptance."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile

import pytest

from ecoscan.config import load_config
from ecoscan.services import academic_report as academic
from ecoscan.services.academic_documents import W, apply_academic_format, verify_academic_docx
from scripts import generate_academic_report as cli

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def copied_evidence(tmp_path):
    original = load_config()
    config = replace(
        original,
        project_root=tmp_path,
        directories={**original.directories, "reports": tmp_path / "reports"},
    )
    manifest = json.loads((ROOT / "docs/aps/evidencias.json").read_text())
    names = set(manifest["source_files"]) | {
        "docs/aps/evidencias.json",
        "docs/aps/relatorio_tecnico.md",
    }
    for name in names:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return config


def test_academic_markdown_matches_checked_metrics_and_exposes_missing_evidence():
    report = academic.build_academic_report(load_config())
    assert report == (ROOT / "docs/aps/relatorio_tecnico.md").read_text()
    assert "| N | 145 | 224 |" in report
    assert "| Rejeitados | 94 | 130 |" in report
    assert "| Cobertura do artefato | 35,17% | 41,96% |" in report
    assert "independent_test=false" in report
    assert "F03 — fracasso real autorizado" in report and "ainda não produzida" in report
    assert "não é o modelo oficial" in re.sub(r"\s+", " ", report.lower())


def test_export_never_treats_ambient_private_reports_as_evidence(copied_evidence):
    private = copied_evidence.directories["reports"] / "project_audit/aps_audit.json"
    private.parent.mkdir(parents=True)
    private.write_text(json.dumps({"items": [], "note": "PRIVATE_AMBIENT_FIXTURE_ONLY"}))
    report = academic.build_academic_report(copied_evidence)
    assert "PRIVATE_AMBIENT_FIXTURE_ONLY" not in report
    assert "Nenhuma atenção alta registrada" not in report


def test_changed_source_cannot_be_relabelled_as_the_frozen_report(copied_evidence):
    source = copied_evidence.project_root / "src/ecoscan/app/pipeline.py"
    source.write_text(source.read_text() + "\n# technical change fixture\n")
    output = copied_evidence.project_root / "should-not-exist.md"
    with pytest.raises(ValueError, match="Source evidence changed"):
        academic.write_academic_report(copied_evidence, output)
    assert not output.exists()


@pytest.mark.parametrize("change", ["independence", "source_sha", "link_sha", "line"])
def test_unproved_acceptance_and_unbound_references_are_rejected(copied_evidence, change):
    path = copied_evidence.project_root / "docs/aps/evidencias.json"
    evidence = json.loads(path.read_text())
    if change == "independence":
        evidence["independent_test"] = True
    elif change == "source_sha":
        evidence["source_sha"] = "a" * 40
    elif change == "link_sha":
        evidence["requirements"][0]["code"]["url"] = (
            "https://github.com/Gabrielhamad/ecoscan/blob/main/config/education.json"
        )
    else:
        location = evidence["requirements"][0]["code"]
        location["line"] += 1
        location["url"] = location["url"].rsplit("#L", 1)[0] + "#L" + str(location["line"])
    path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError):
        academic.build_academic_report(copied_evidence)


def test_code_appendix_exports_committed_public_code_and_has_reproducible_bytes(
    tmp_path, monkeypatch
):
    source = tmp_path / "source"
    (source / "src").mkdir(parents=True)
    (source / "src/entry.py").write_text("PUBLIC_COMMITTED_FIXTURE = True\n")
    (source / ".env").write_text("PRIVATE_FIXTURE_ONLY")
    (source / "photo.png").write_bytes(b"not a real photo, excluded anyway")
    for args in [
        ("init",),
        ("config", "user.name", "Fixture"),
        ("config", "user.email", "fixture@example.invalid"),
        ("add", "."),
        ("commit", "-m", "technical fixture"),
    ]:
        subprocess.run(["git", *args], cwd=source, check=True, capture_output=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source).decode().strip()
    monkeypatch.setattr(academic, "FROZEN_SOURCE_SHA", sha)
    monkeypatch.setattr(academic, "checked_evidence", lambda config: {})
    (source / "src/entry.py").write_text("UNCOMMITTED_PRIVATE_FIXTURE_ONLY")
    config = replace(load_config(), project_root=source)
    first = academic.write_code_appendix(config, tmp_path / "one.zip")
    second = academic.write_code_appendix(config, tmp_path / "two.zip")
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert set(archive.namelist()) == {"src/entry.py", "APENDICE_MANIFEST.json"}
        data = archive.read("src/entry.py")
        assert data == b"PUBLIC_COMMITTED_FIXTURE = True\n"
        manifest = json.loads(archive.read("APENDICE_MANIFEST.json"))
        assert manifest["source_sha"] == sha
        assert manifest["files"]["src/entry.py"] == hashlib.sha256(data).hexdigest()


def test_docx_format_checks_actual_document_and_styles_without_claiming_visual_acceptance(tmp_path):
    path = tmp_path / "fixture.docx"
    ns = W[1:-1]
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "word/document.xml",
            f'<w:document xmlns:w="{ns}"><w:body><w:p><w:pPr/><w:r><w:rPr/></w:r></w:p><w:sectPr/></w:body></w:document>',
        )
        archive.writestr(
            "word/styles.xml",
            f'<w:styles xmlns:w="{ns}"><w:style><w:pPr/><w:rPr><w:rFonts w:ascii="Calibri"/><w:sz w:val="20"/></w:rPr></w:style></w:styles>',
        )
        archive.writestr(
            "docProps/core.xml",
            '<core xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>technical-generator</dc:creator></core>',
        )
    apply_academic_format(path)
    result = verify_academic_docx(path)
    assert result["ooxml_format"] == "passed" and result["margins_cm"] == 2.5
    assert result["official_2026_template"] == "not_available"
    assert result["visual_review_on_presentation_pc"] == "manual_pending"
    assert result["academic_submission_ready"] is False
    with zipfile.ZipFile(path) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    document = ET.fromstring(contents["word/document.xml"])
    document.find(".//" + W + "pgMar").set(W + "left", "1440")
    contents["word/document.xml"] = ET.tostring(document)
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in contents.items():
            archive.writestr(name, content)
    with pytest.raises(ValueError, match="page/margins"):
        verify_academic_docx(path)


def test_docx_tool_failure_keeps_markdown_and_reports_no_approval(tmp_path, monkeypatch, capsys):
    def unavailable(*args):
        raise RuntimeError("PRIVATE_PATH_FIXTURE_ONLY")

    monkeypatch.setattr("ecoscan.services.academic_documents.write_academic_docx", unavailable)
    output = tmp_path / "report.md"
    assert cli.main(["--output", str(output), "--docx"]) == 1
    assert output.exists() and not output.with_suffix(".docx").exists()
    message = capsys.readouterr().out
    assert "PRIVATE_PATH_FIXTURE_ONLY" not in message and "Nenhum aceite" in message


def test_delivered_documents_and_code_match_the_review_manifest():
    folder = ROOT / "docs/aps"
    artifacts = json.loads((folder / "artefatos.json").read_text())
    assert artifacts["source_sha"] == academic.FROZEN_SOURCE_SHA
    assert artifacts["academic_submission_ready"] is False
    for name, record in artifacts["files"].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == record["sha256"]
    for name in ("relatorio_aps.docx", "ficha_aps_preparatoria.docx"):
        assert verify_academic_docx(folder / name)["ooxml_format"] == "passed"
    with zipfile.ZipFile(folder / "apendice_codigo.zip") as archive:
        manifest = json.loads(archive.read("APENDICE_MANIFEST.json"))
        assert manifest["source_sha"] == academic.FROZEN_SOURCE_SHA
        assert len(manifest["files"]) == artifacts["code_appendix_files"]
        assert set(archive.namelist()) == set(manifest["files"]) | {"APENDICE_MANIFEST.json"}
        for name, checksum in manifest["files"].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == checksum
            assert Path(name).suffix in {
                ".py",
                ".sql",
                ".css",
                ".html",
                ".toml",
                ".txt",
            } or name.endswith("LICENSE-CLIP")
