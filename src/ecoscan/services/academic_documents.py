"""Optional DOCX export/OOXML checks; stdlib plus a development Pandoc executable."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def apply_academic_format(path: Path) -> None:
    """Declare the supplied format without claiming an unavailable official template."""
    with zipfile.ZipFile(path) as archive:
        data = {name: archive.read(name) for name in archive.namelist()}
    for name in ("word/styles.xml", "word/document.xml"):
        root = ET.fromstring(data[name])
        for props in root.iter(W + "rPr"):
            fonts = props.find(W + "rFonts")
            if fonts is None:
                fonts = ET.SubElement(props, W + "rFonts")
            fonts.attrib.clear()
            fonts.attrib.update({W + key: "Arial" for key in ("ascii", "hAnsi", "cs", "eastAsia")})
            for tag in ("sz", "szCs"):
                size = props.find(W + tag)
                if size is None:
                    size = ET.SubElement(props, W + tag)
                size.set(W + "val", "24")
        for props in root.iter(W + "pPr"):
            spacing = props.find(W + "spacing")
            if spacing is None:
                spacing = ET.SubElement(props, W + "spacing")
            spacing.attrib.clear()
            spacing.attrib.update(
                {W + "line": "360", W + "lineRule": "auto", W + "before": "0", W + "after": "0"}
            )
        for section in root.iter(W + "sectPr"):
            size = section.find(W + "pgSz")
            if size is None:
                size = ET.SubElement(section, W + "pgSz")
            size.attrib.clear()
            size.attrib.update({W + "w": "11906", W + "h": "16838"})
            margins = section.find(W + "pgMar")
            if margins is None:
                margins = ET.SubElement(section, W + "pgMar")
            for side in ("top", "bottom", "left", "right"):
                margins.set(W + side, "1417")
        for table in root.iter(W + "tbl"):
            for index, row in enumerate(table.findall(W + "tr")):
                props = row.find(W + "trPr")
                if props is None:
                    props = ET.Element(W + "trPr")
                    row.insert(0, props)
                if props.find(W + "cantSplit") is None:
                    ET.SubElement(props, W + "cantSplit")
                if index == 0 and props.find(W + "tblHeader") is None:
                    ET.SubElement(props, W + "tblHeader")
        data[name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    # Do not label the OS account or generator as a student/academic author.
    core = ET.fromstring(data["docProps/core.xml"])
    for node in core:
        if node.tag.rsplit("}", 1)[-1] in {"creator", "lastModifiedBy"}:
            node.text = ""
    data["docProps/core.xml"] = ET.tostring(core, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in data.items():
            archive.writestr(name, content)


def verify_academic_docx(path: Path) -> dict:
    """Check actual OOXML declarations; rendering/official ABNT review stays separate."""
    with zipfile.ZipFile(path) as archive:
        roots = [
            ET.fromstring(archive.read(name)) for name in ("word/styles.xml", "word/document.xml")
        ]
        core = ET.fromstring(archive.read("docProps/core.xml"))
    fonts = [node for root in roots for node in root.iter(W + "rFonts")]
    sizes = [node for root in roots for tag in ("sz", "szCs") for node in root.iter(W + tag)]
    spacings = [node for root in roots for node in root.iter(W + "spacing")]
    sections = list(roots[1].iter(W + "sectPr"))
    if (
        not fonts
        or any(
            node.get(W + key) != "Arial"
            for node in fonts
            for key in ("ascii", "hAnsi", "cs", "eastAsia")
        )
        or not sizes
        or any(node.get(W + "val") != "24" for node in sizes)
        or not spacings
        or any(
            node.get(W + "line") != "360" or node.get(W + "lineRule") != "auto" for node in spacings
        )
        or not sections
    ):
        raise ValueError("DOCX font/size/spacing differs from the supplied academic format")
    for section in sections:
        size, margins = section.find(W + "pgSz"), section.find(W + "pgMar")
        if (
            size is None
            or (size.get(W + "w"), size.get(W + "h")) != ("11906", "16838")
            or margins is None
            or any(margins.get(W + side) != "1417" for side in ("top", "bottom", "left", "right"))
        ):
            raise ValueError("DOCX page/margins differ from the supplied format")
    for table in roots[1].iter(W + "tbl"):
        for index, row in enumerate(table.findall(W + "tr")):
            props = row.find(W + "trPr")
            if (
                props is None
                or props.find(W + "cantSplit") is None
                or (index == 0 and props.find(W + "tblHeader") is None)
            ):
                raise ValueError("DOCX table must repeat headers and keep rows together")
    if any(
        node.text for node in core if node.tag.rsplit("}", 1)[-1] in {"creator", "lastModifiedBy"}
    ):
        raise ValueError("Do not infer an academic author from generator metadata")
    font_tool = shutil.which("fc-match")
    available = None
    if font_tool:
        families = subprocess.run(
            [font_tool, "--format=%{family}", "Arial"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
        available = "arial" in {part.strip().casefold() for part in families.split(",")}
    return {
        "ooxml_format": "passed",
        "font_declared": "Arial",
        "font_points": 12,
        "line_spacing": 1.5,
        "page": "A4",
        "margins_cm": 2.5,
        "arial_available_on_export_host": available,
        "visual_review_on_presentation_pc": "manual_pending",
        "official_2026_template": "not_available",
        "academic_submission_ready": False,
    }


def write_academic_docx(markdown: Path, output: Path) -> dict:
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        raise RuntimeError("Pandoc unavailable; Markdown remains ready for conversion")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".academic-docx-") as temp:
        draft = Path(temp) / "review.docx"
        subprocess.run(
            [
                pandoc,
                str(markdown.resolve()),
                "--from=markdown",
                "--to=docx",
                "--standalone",
                "--no-highlight",
                "--metadata=lang:pt-BR",
                "--output=" + str(draft),
            ],
            cwd=markdown.parent,
            check=True,
            capture_output=True,
            timeout=60,
        )
        apply_academic_format(draft)
        result = verify_academic_docx(draft)
        draft.replace(output)
    output.with_suffix(".format.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result
