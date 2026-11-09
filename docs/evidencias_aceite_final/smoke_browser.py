"""Optional local-only Playwright smoke. Generated upload has no material ground truth."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8519")
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_sha = "89622ec714b815c216a9215ab9ba69999b39c6b8"
    unchanged = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            source_sha,
            "--",
            "src/ecoscan",
            "config",
            "models/semantic-v1",
            "streamlit_app.py",
        ],
        cwd=Path(__file__).resolve().parents[2],
    )
    if unchanged.returncode:
        raise ValueError("Application files differ from the expected frozen source SHA")
    parsed = urlsplit(args.url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"localhost", "127.0.0.1"}
        or parsed.query
        or parsed.username
    ):
        raise ValueError("Audit smoke accepts only an explicit local HTTP server")
    from playwright.sync_api import sync_playwright, expect

    results, page_errors, blocked_requests = [], [], []

    def record(identifier: str, title: str, passed: bool, **observations) -> None:
        results.append(
            {
                "id": identifier,
                "title": title,
                "status": "PASS" if passed else "FAIL",
                "observations": observations,
            }
        )

    with (
        tempfile.TemporaryDirectory(prefix="ecoscan-browser-audit-") as temp,
        sync_playwright() as playwright,
    ):
        folder = Path(temp)
        image = Image.new("RGB", (96, 80), "white")
        image.paste((40, 100, 60), (25, 15, 70, 65))
        image.save(folder / "technical.png")
        (folder / "corrupt.png").write_bytes(b"not a valid PNG")
        browser = playwright.chromium.launch(
            executable_path=args.chromium, headless=True, args=["--no-sandbox"]
        )
        page = browser.new_page(viewport={"width": 1280, "height": 900}, permissions=[])
        page.on("pageerror", lambda error: page_errors.append(type(error).__name__))

        def route_request(route):
            if route.request.url.startswith(
                (args.url, args.url.replace("http:", "ws:"), "data:", "blob:")
            ):
                route.continue_()
            else:
                blocked_requests.append(1)
                route.abort()

        page.route("**/*", route_request)
        page.goto(args.url, wait_until="networkidle")
        expect(page.locator("input[type=file]")).to_have_count(1, timeout=30000)
        record(
            "BROWSER-01",
            "Visitante abre sem tela branca",
            page.locator("[data-testid=stException]").count() == 0,
        )
        page.locator("input[type=file]").first.set_input_files(folder / "corrupt.png")
        expect(page.get_by_text(re.compile("IMG-001 - Imagem inválida"))).to_be_visible(
            timeout=30000
        )
        record(
            "BROWSER-02",
            "Arquivo inválido tem erro controlado",
            page.locator("[data-testid=stException]").count() == 0,
        )
        material = page.get_by_role("combobox", name="Qual material você identificou na foto?")
        record(
            "BROWSER-03", "Correção manual acessível após arquivo inválido", material.count() > 0
        )
        page.get_by_role("tab", name="Descarte", exact=True).click()
        expect(page.get_by_role("heading", name="Descarte responsável", exact=True)).to_be_visible()
        record(
            "BROWSER-04",
            "Aba Descarte oferece escolha de material após falha",
            page.get_by_role("combobox").count() > 0,
        )
        page.get_by_role("tab", name="Escanear", exact=True).click()
        page.locator("input[type=file]").first.set_input_files(folder / "technical.png")
        expect(material).to_be_visible(timeout=120000)
        record(
            "BROWSER-05",
            "Análise local permite confirmação",
            page.locator("[data-testid=stException]").count() == 0,
        )
        material.fill("Vidro")
        material.press("ArrowDown")
        page.get_by_role("option", name="Vidro", exact=True).click()
        expect(page.get_by_text("Vidro: Lixeira verde.", exact=True)).to_be_visible(timeout=30000)
        record("BROWSER-06", "Escolha humana de Vidro mostra lixeira verde", True)
        page.get_by_role("tab", name="Mapa", exact=True).click()
        expect(page.get_by_role("heading", name="Descarte em São Paulo", exact=True)).to_be_visible(
            timeout=30000
        )
        page.get_by_role("tab", name="Escanear", exact=True).click()
        expect(page.get_by_text("Vidro: Lixeira verde.", exact=True)).to_be_visible(timeout=30000)
        record("BROWSER-07", "Navegação mantém foto/resultado e escolha humana", True)
        page.reload(wait_until="networkidle")
        expect(
            page.get_by_text("Tire ou envie uma foto do resíduo para analisar.", exact=True)
        ).to_be_visible(timeout=30000)
        record(
            "BROWSER-10",
            "Nova sessão após reload pede reenvio sem tela branca",
            material.count() == 0 and page.locator("[data-testid=stException]").count() == 0,
            previous_analysis_restored=False,
        )
        second = browser.new_page(viewport={"width": 1280, "height": 900}, permissions=[])
        second.route("**/*", route_request)
        second.goto(args.url, wait_until="networkidle")
        expect(second.locator("input[type=file]")).to_have_count(1, timeout=30000)
        record(
            "BROWSER-11",
            "Outro contexto visitante não herda captura ou escolha humana",
            second.locator("input[type=file]").evaluate("element => element.files.length") == 0
            and second.get_by_role(
                "combobox", name="Qual material você identificou na foto?"
            ).count()
            == 0,
            scope="fresh_browser_context_not_real_account_isolation",
        )
        second.close()
        page.goto(args.url + "/?profile=admin_secretaria", wait_until="networkidle")
        expect(page.locator("input[type=file]")).to_have_count(1, timeout=30000)
        record(
            "BROWSER-08",
            "Query de perfil não libera Gestão",
            page.get_by_role("tab", name="Gestão", exact=True).count() == 0,
        )
        record(
            "BROWSER-09",
            "Navegador sem exceções não tratadas",
            not page_errors,
            uncaught_page_errors=len(page_errors),
            external_browser_requests_blocked=len(blocked_requests),
        )
        browser.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "expected_source_sha": source_sha,
                "working_tree_application_matches_source": True,
                "generated_at_local": datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(
                    timespec="seconds"
                ),
                "scope": "Linux Chromium local, fixture only; not a real phone or published acceptance",
                "real_accounts_used": False,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {state: sum(row["status"] == state for row in results) for state in ("PASS", "FAIL")}
        )
    )
    return 2 if any(row["status"] == "FAIL" for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
