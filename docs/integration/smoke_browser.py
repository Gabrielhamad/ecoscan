"""Local-only candidate smoke; generated pixels do not measure field accuracy."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlsplit
import zipfile

from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8519")
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    origin = urlsplit(args.url)
    if (
        origin.scheme != "http"
        or origin.hostname not in {"127.0.0.1", "localhost"}
        or origin.query
        or origin.username
    ):
        raise ValueError("Only an explicit local HTTP server is allowed")
    from playwright.sync_api import expect, sync_playwright

    root = Path(__file__).resolve().parents[2]
    files = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "src", "config", "tests"],
        cwd=root,
        text=True,
    ).splitlines()
    hashes = {
        name: {"sha256": hashlib.sha256((root / name).read_bytes()).hexdigest()} for name in files
    }
    results, errors = [], []

    def record(identifier: str, title: str, **observations) -> None:
        print(f"{identifier}: {title}", flush=True)
        results.append(
            {"id": identifier, "title": title, "status": "PASS", "observations": observations}
        )

    with (
        tempfile.TemporaryDirectory(prefix="ecoscan-integration-") as folder,
        sync_playwright() as playwright,
    ):
        temporary = Path(folder)
        image = Image.new("RGB", (96, 80), "white")
        image.paste((40, 100, 60), (25, 15, 70, 65))
        image.save(temporary / "technical.png")
        (temporary / "invalid.png").write_bytes(b"not a valid PNG")
        browser = playwright.chromium.launch(
            executable_path=args.chromium, headless=True, args=["--no-sandbox"]
        )
        page = browser.new_page(viewport={"width": 1280, "height": 900}, permissions=[])
        page.on("pageerror", lambda error: errors.append(type(error).__name__))

        def route_request(route):
            target = urlsplit(route.request.url)
            if target.scheme in {"data", "blob"} or (
                target.hostname == origin.hostname and target.port == origin.port
            ):
                route.continue_()
            else:
                route.abort()

        page.route("**/*", route_request)
        page.goto(args.url, wait_until="networkidle")
        upload = page.locator("input[type=file]")
        manual = page.get_by_role("combobox", name="Qual material você confirmou?", exact=True)
        expect(upload).to_have_count(1, timeout=30000)
        expect(manual).to_be_visible()
        record("B01", "Visitante abre e pode consultar sem foto")
        upload.set_input_files(temporary / "invalid.png")
        expect(page.get_by_text(re.compile("IMG-001 - Imagem inválida"))).to_be_visible(
            timeout=30000
        )
        expect(manual).to_be_visible()
        record("B02", "Upload inválido mantém correção manual")

        def choose(label: str) -> None:
            manual.fill(label)
            manual.press("ArrowDown")
            page.get_by_role("option", name=label, exact=True).click()

        choose("Vidro")
        expect(page.get_by_text(re.compile("Material confirmado por você: Vidro"))).to_be_visible()
        expect(
            page.get_by_text(re.compile("Material confirmado por você: Vidro.*Lixeira verde"))
        ).to_be_visible()
        record("B03", "Correção após erro mostra Vidro e lixeira verde")
        page.get_by_role("tab", name="Descarte", exact=True).click()
        expect(manual).to_be_visible()
        choose("Pilha / bateria")
        expect(page.get_by_text(re.compile("Material confirmado por você: Pilha"))).to_be_visible()
        record("B04", "Aba Descarte oferece consulta humana e coleta especial")
        page.get_by_role("tab", name="Escanear", exact=True).click()
        upload.set_input_files(temporary / "technical.png")
        expect(
            page.get_by_role("button", name="Baixar evidências do processamento (ZIP)", exact=True)
        ).to_be_visible(timeout=120000)
        expect(
            page.get_by_role("heading", name="Preparação para reconhecimento", exact=True)
        ).to_be_visible()
        expect(page.get_by_text(re.compile("Melhor correspondência:"))).to_be_visible(
            timeout=120000
        )
        record("B05", "Pipeline e ONNX local abrem com as duas trilhas visíveis")

        def manifest(name: str) -> dict:
            with page.expect_download() as event:
                page.get_by_role(
                    "button", name="Baixar evidências do processamento (ZIP)", exact=True
                ).click()
            target = temporary / name
            event.value.save_as(target)
            with zipfile.ZipFile(target) as archive:
                return json.loads(archive.read("manifest.json"))

        before = manifest("control.zip")
        choose("Vidro")
        page.get_by_text("Laboratório de processamento de imagens", exact=True).click()
        experimental = page.get_by_role("combobox", name="Filtro", exact=True)
        experimental.fill("gaussian")
        experimental.press("ArrowDown")
        page.get_by_role("option", name="gaussian", exact=True).click()
        expect(
            page.get_by_role("button", name="Baixar evidências do processamento (ZIP)", exact=True)
        ).to_be_visible(timeout=30000)
        expect(
            page.get_by_text(re.compile("Material confirmado por você: Vidro"))
        ).not_to_be_visible(timeout=30000)
        after = manifest("gaussian.zip")
        assert before["classifier_input_sha256"] == after["classifier_input_sha256"]
        assert before["stages"][1]["after"]["sha256"] != after["stages"][1]["after"]["sha256"]
        record(
            "B06",
            "Troca de filtro altera PNG didático, preserva RGB oficial e limpa confirmação",
            classifier_input_sha256=after["classifier_input_sha256"],
        )
        choose("Vidro")
        page.get_by_role("tab", name="Mapa", exact=True).click()
        expect(
            page.get_by_role("heading", name="Descarte em São Paulo", exact=True)
        ).to_be_visible()
        page.get_by_role("tab", name="Escanear", exact=True).click()
        expect(page.get_by_text(re.compile("Material confirmado por você: Vidro"))).to_be_visible()
        record("B07", "Navegação preserva resultado e escolha humana")
        page.get_by_role("button", name="Nova foto", exact=True).click()
        expect(
            page.get_by_text(re.compile("Material confirmado por você: Vidro"))
        ).not_to_be_visible()
        expect(manual).to_be_visible()
        record("B08", "Nova foto limpa a análise sem impedir consulta manual")
        page.goto(args.url + "/?profile=admin_secretaria", wait_until="networkidle")
        expect(page.locator("input[type=file]")).to_have_count(1, timeout=30000)
        assert page.get_by_role("tab", name="Gestão", exact=True).count() == 0
        assert page.locator("[data-testid=stException]").count() == 0 and not errors
        record("B09", "Query não eleva visitante e não há exceções JS/Streamlit não tratadas")
        browser.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_files_sha256": hashes,
                "scope": "Local Linux Chromium; technical fixtures only",
                "real_accounts_or_production_used": False,
                "independent_test": False,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(results)} local browser checks passed; no field accuracy measured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
