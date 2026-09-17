from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "EcoScanDatasetBuilder/0.2 (academic local dataset builder; Wikimedia Commons API)"
SUPPORTED_MIME_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


@dataclass(frozen=True)
class Candidate:
    title: str
    class_id: str
    source_category: str
    url: str
    mime: str
    width: int
    height: int
    license_short_name: str
    license_url: str
    artist: str
    credit: str
    description_url: str


@dataclass(frozen=True)
class SourceClass:
    class_id: str
    categories: tuple[str, ...]
    search_terms: tuple[str, ...]


@dataclass(frozen=True)
class DownloadedImage:
    class_id: str
    local_path: str
    title: str
    source_category: str
    file_url: str
    description_url: str
    mime: str
    width: int
    height: int
    sha256: str
    license_short_name: str
    license_url: str
    artist: str
    credit: str


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metadata_value(metadata: dict[str, Any], key: str) -> str:
    if not isinstance(metadata, dict):
        return ""
    value = metadata.get(key, {})
    if isinstance(value, dict):
        return str(value.get("value", "")).strip()
    return ""


def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    encoded = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{encoded}",
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _download_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def _rate_limit_delay_seconds(exc: urllib.error.HTTPError) -> int:
    retry_after = exc.headers.get("Retry-After", "")
    try:
        return max(5, min(15, int(retry_after)))
    except ValueError:
        return 10


def _sanitize_filename(value: str) -> str:
    value = value.replace("File:", "")
    value = urllib.parse.unquote(value)
    value = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", value)
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value[:64] or "wikimedia-image"


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalize_values(values: Any) -> tuple[str, ...]:
    if not isinstance(values, list):
        return ()
    return tuple(str(value).strip() for value in values if str(value).strip())


def _normalize_source_classes(raw_classes: dict[str, Any]) -> list[SourceClass]:
    source_classes: list[SourceClass] = []
    for class_id, value in raw_classes.items():
        if isinstance(value, list):
            categories = _normalize_values(value)
            search_terms: tuple[str, ...] = ()
        elif isinstance(value, dict):
            categories = _normalize_values(value.get("categories", []))
            search_terms = _normalize_values(value.get("search_terms", []))
        else:
            raise ValueError(f"Invalid source configuration for class: {class_id}")

        if not categories and not search_terms:
            raise ValueError(f"No Wikimedia sources configured for class: {class_id}")
        source_classes.append(SourceClass(str(class_id), categories, search_terms))
    return source_classes


def _imageinfo_params(thumb_width: int) -> dict[str, Any]:
    return {
        "prop": "imageinfo",
        "iiprop": "url|size|mime|mediatype|extmetadata",
        "iiurlwidth": str(thumb_width),
        "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|Credit",
    }


def _candidate_from_page(page: dict[str, Any], class_id: str, category: str) -> Candidate | None:
    imageinfo = page.get("imageinfo") or []
    if not imageinfo:
        return None

    info = imageinfo[0]
    mime = str(info.get("mime", "")).lower()
    if mime not in SUPPORTED_MIME_EXTENSIONS:
        return None

    metadata = info.get("extmetadata", {})
    license_short_name = _metadata_value(metadata, "LicenseShortName")
    license_url = _metadata_value(metadata, "LicenseUrl")

    # Keep only files with machine-readable licensing text. CC/Public Domain files are
    # common here, but the manifest still preserves exact per-file terms for review.
    if not license_short_name and not license_url:
        return None

    return Candidate(
        title=str(page.get("title", "")),
        class_id=class_id,
        source_category=category,
        url=str(info.get("thumburl") or info.get("url") or ""),
        mime=mime,
        width=int(info.get("thumbwidth") or info.get("width") or 0),
        height=int(info.get("thumbheight") or info.get("height") or 0),
        license_short_name=license_short_name,
        license_url=license_url,
        artist=_metadata_value(metadata, "Artist"),
        credit=_metadata_value(metadata, "Credit"),
        description_url=str(info.get("descriptionurl", "")),
    )


def collect_candidates(
    *,
    api_url: str,
    class_id: str,
    category: str,
    max_candidates: int,
    thumb_width: int,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    continuation: dict[str, Any] = {}

    while len(candidates) < max_candidates:
        params: dict[str, Any] = {
            "action": "query",
            "format": "json",
            "generator": "categorymembers",
            "gcmtitle": f"Category:{category}",
            "gcmtype": "file",
            "gcmnamespace": "6",
            "gcmlimit": "50",
        }
        params.update(_imageinfo_params(thumb_width))
        params.update(continuation)

        data = _request_json(api_url, params)
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            candidate = _candidate_from_page(page, class_id, category)
            if candidate and candidate.url:
                candidates.append(candidate)
                if len(candidates) >= max_candidates:
                    break

        if "continue" not in data:
            break
        continuation = data["continue"]
        time.sleep(0.2)

    return candidates


def _collect_candidates_by_titles(
    *,
    api_url: str,
    class_id: str,
    source_name: str,
    titles: list[str],
    thumb_width: int,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for index in range(0, len(titles), 50):
        batch = titles[index:index + 50]
        params: dict[str, Any] = {
            "action": "query",
            "format": "json",
            "titles": "|".join(batch),
        }
        params.update(_imageinfo_params(thumb_width))
        data = _request_json(api_url, params)
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            candidate = _candidate_from_page(page, class_id, source_name)
            if candidate and candidate.url:
                candidates.append(candidate)
    return candidates


def collect_candidates_from_search(
    *,
    api_url: str,
    class_id: str,
    search_term: str,
    max_candidates: int,
    thumb_width: int,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    offset = 0

    while len(candidates) < max_candidates:
        params: dict[str, Any] = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srnamespace": "6",
            "srsearch": search_term,
            "srlimit": "50",
            "sroffset": str(offset),
        }
        data = _request_json(api_url, params)
        results = data.get("query", {}).get("search", [])
        titles = [str(item.get("title", "")) for item in results if str(item.get("title", "")).startswith("File:")]
        if not titles:
            break

        candidates.extend(
            _collect_candidates_by_titles(
                api_url=api_url,
                class_id=class_id,
                source_name=f"search:{search_term}",
                titles=titles,
                thumb_width=thumb_width,
            )
        )

        if "continue" not in data:
            break
        offset = int(data["continue"].get("sroffset", offset + len(titles)))
        time.sleep(0.2)

    return candidates[:max_candidates]


def _candidate_text(candidate: Candidate) -> str:
    return " ".join(
        [
            candidate.title,
            candidate.url,
            candidate.description_url,
        ]
    ).lower()


def _terms_for_class(term_map: dict[str, tuple[str, ...]], class_id: str) -> tuple[str, ...]:
    return (*term_map.get("_all", ()), *term_map.get(class_id, ()))


def _candidate_matches_class(
    candidate: Candidate,
    include_terms: tuple[str, ...],
    reject_terms: tuple[str, ...] = (),
) -> bool:
    text = _candidate_text(candidate)
    if any(term.lower() in text for term in reject_terms):
        return False
    if not include_terms:
        return True
    return any(term.lower() in text for term in include_terms)


def _existing_count(output_dir: Path, class_id: str) -> int:
    class_dir = output_dir / class_id
    if not class_dir.exists():
        return 0
    return sum(1 for path in class_dir.iterdir() if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png"})


def _existing_file_hashes(output_dir: Path) -> set[str]:
    hashes: set[str] = set()
    if not output_dir.exists():
        return hashes
    for path in output_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        try:
            hashes.add(_sha256(path.read_bytes()))
        except OSError:
            continue
    return hashes


def _downloaded_from_row(row: dict[str, Any]) -> DownloadedImage | None:
    try:
        return DownloadedImage(
            class_id=str(row.get("class_id", "")),
            local_path=str(row.get("local_path", "")),
            title=str(row.get("title", "")),
            source_category=str(row.get("source_category", "")),
            file_url=str(row.get("file_url", "")),
            description_url=str(row.get("description_url", "")),
            mime=str(row.get("mime", "")),
            width=int(row.get("width", 0)),
            height=int(row.get("height", 0)),
            sha256=str(row.get("sha256", "")),
            license_short_name=str(row.get("license_short_name", "")),
            license_url=str(row.get("license_url", "")),
            artist=str(row.get("artist", "")),
            credit=str(row.get("credit", "")),
        )
    except (TypeError, ValueError):
        return None


def _load_existing_manifest(report_dir: Path) -> list[DownloadedImage]:
    manifest_path = report_dir / "wikimedia_capture_manifest.json"
    if not manifest_path.exists():
        return []
    try:
        raw_rows = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw_rows, list):
        return []
    rows: list[DownloadedImage] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        image = _downloaded_from_row(row)
        if image and _manifest_file_exists(image.local_path):
            rows.append(image)
    return rows


def _manifest_file_exists(local_path: str) -> bool:
    path = Path(local_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.exists()


def _merge_downloads(rows: list[DownloadedImage]) -> list[DownloadedImage]:
    merged: list[DownloadedImage] = []
    seen: set[str] = set()
    for row in rows:
        key = row.sha256 or f"{row.class_id}:{row.title}:{row.local_path}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
    return merged


def capture_dataset(
    *,
    source_config_path: Path,
    output_dir: Path,
    report_dir: Path,
    images_per_class: int,
    thumb_width: int,
    delay_seconds: float,
    selected_classes: tuple[str, ...] | None = None,
) -> list[DownloadedImage]:
    source_config = _read_json(source_config_path)
    api_url = source_config.get("api_url", COMMONS_API)
    source_classes = _normalize_source_classes(source_config["classes"])
    title_filters = {
        str(class_id): tuple(str(term).strip() for term in terms if str(term).strip())
        for class_id, terms in dict(source_config.get("title_include_any", {})).items()
        if isinstance(terms, list)
    }
    reject_filters = {
        str(class_id): tuple(str(term).strip() for term in terms if str(term).strip())
        for class_id, terms in dict(source_config.get("title_reject_any", {})).items()
        if isinstance(terms, list)
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    existing_manifest = _load_existing_manifest(report_dir)
    downloaded: list[DownloadedImage] = []
    seen_titles: set[str] = {row.title for row in existing_manifest if row.title}
    seen_hashes: set[str] = {row.sha256 for row in existing_manifest if row.sha256}
    seen_hashes.update(_existing_file_hashes(output_dir))

    selected_class_set = set(selected_classes or ())

    for source_class in source_classes:
        class_id = source_class.class_id
        if selected_class_set and class_id not in selected_class_set:
            continue

        class_dir = output_dir / class_id
        class_dir.mkdir(parents=True, exist_ok=True)

        already_present = _existing_count(output_dir, class_id)
        needed = max(0, images_per_class - already_present)
        if needed == 0:
            print(f"{class_id}: already has {already_present} images; skipping.")
            continue

        print(f"{class_id}: collecting {needed} image(s).")
        sequence = already_present + 1

        source_sequence = [("category", item) for item in source_class.categories]
        source_sequence.extend(("search", item) for item in source_class.search_terms)

        for source_kind, source_name in source_sequence:
            if needed <= 0:
                break

            try:
                if source_kind == "search":
                    candidates = collect_candidates_from_search(
                        api_url=api_url,
                        class_id=class_id,
                        search_term=source_name,
                        max_candidates=needed * 4,
                        thumb_width=thumb_width,
                    )
                else:
                    candidates = collect_candidates(
                        api_url=api_url,
                        class_id=class_id,
                        category=source_name,
                        max_candidates=needed * 4,
                        thumb_width=thumb_width,
                    )
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                print(f"  {source_name}: failed to collect candidates: {exc}")
                continue

            rate_limit_failures = 0
            for candidate in candidates:
                if needed <= 0:
                    break
                if candidate.title in seen_titles:
                    continue
                if not _candidate_matches_class(
                    candidate,
                    title_filters.get(class_id, ()),
                    _terms_for_class(reject_filters, class_id),
                ):
                    continue

                try:
                    image_bytes = _download_bytes(candidate.url)
                except urllib.error.HTTPError as exc:
                    if exc.code == 429:
                        rate_limit_failures += 1
                        retry_delay = _rate_limit_delay_seconds(exc)
                        print(f"  {candidate.title}: rate limited; waiting {retry_delay}s and skipping this source.")
                        time.sleep(retry_delay)
                        print(f"  {source_name}: skipped after Wikimedia rate-limit response.")
                        break
                    else:
                        print(f"  {candidate.title}: download failed: {exc}")
                        continue
                except (urllib.error.URLError, TimeoutError) as exc:
                    print(f"  {candidate.title}: download failed: {exc}")
                    continue

                digest = _sha256(image_bytes)
                if digest in seen_hashes:
                    continue

                extension = SUPPORTED_MIME_EXTENSIONS[candidate.mime]
                filename = f"{class_id}_{sequence:04d}_{_sanitize_filename(candidate.title)}{extension}"
                local_path = class_dir / filename
                local_path.write_bytes(image_bytes)

                downloaded.append(
                    DownloadedImage(
                        class_id=class_id,
                        local_path=_safe_relative(local_path, PROJECT_ROOT),
                        title=candidate.title,
                        source_category=candidate.source_category,
                        file_url=candidate.url,
                        description_url=candidate.description_url,
                        mime=candidate.mime,
                        width=candidate.width,
                        height=candidate.height,
                        sha256=digest,
                        license_short_name=candidate.license_short_name,
                        license_url=candidate.license_url,
                        artist=candidate.artist,
                        credit=candidate.credit,
                    )
                )
                seen_titles.add(candidate.title)
                seen_hashes.add(digest)
                sequence += 1
                needed -= 1
                print(f"  saved {local_path.name}")
                write_manifest(existing_manifest, downloaded, report_dir, source_config)
                time.sleep(delay_seconds)

        if needed > 0:
            print(f"{class_id}: still missing {needed} image(s); review categories or add another source.")
        write_manifest(existing_manifest, downloaded, report_dir, source_config)

    write_manifest(existing_manifest, downloaded, report_dir, source_config)
    return downloaded


def write_manifest(
    existing_manifest: list[DownloadedImage],
    downloaded: list[DownloadedImage],
    report_dir: Path,
    source_config: dict[str, Any] | None = None,
) -> None:
    json_path = report_dir / "wikimedia_capture_manifest.json"
    csv_path = report_dir / "wikimedia_capture_manifest.csv"
    summary_path = report_dir / "web_capture_summary.md"

    all_images = _merge_downloads([*existing_manifest, *downloaded])
    rows = [image.__dict__ for image in all_images]
    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    fieldnames = [
        "class_id",
        "local_path",
        "title",
        "source_category",
        "file_url",
        "description_url",
        "mime",
        "width",
        "height",
        "sha256",
        "license_short_name",
        "license_url",
        "artist",
        "credit",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    total_counts: dict[str, int] = {}
    new_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for image in all_images:
        total_counts[image.class_id] = total_counts.get(image.class_id, 0) + 1
    for image in downloaded:
        new_counts[image.class_id] = new_counts.get(image.class_id, 0) + 1
        source_counts[image.source_category] = source_counts.get(image.source_category, 0) + 1

    provider = source_config.get("provider", "Wikimedia Commons") if source_config else "Wikimedia Commons"
    provider_url = source_config.get("provider_url", "https://commons.wikimedia.org/") if source_config else "https://commons.wikimedia.org/"

    lines = [
        "# Captura web do dataset EcoScan",
        "",
        f"Fonte principal: [{provider}]({provider_url}).",
        "",
        "Esta base é um conjunto inicial para desenvolvimento e avaliação acadêmica. Antes do treino final, revise cada imagem visualmente e mantenha o manifesto de atribuição junto ao projeto.",
        "",
        "## Imagens novas nesta execução",
        "",
    ]
    if new_counts:
        for class_id, count in sorted(new_counts.items()):
            lines.append(f"- {class_id}: {count}")
    else:
        lines.append("- Nenhuma imagem nova capturada.")
    lines.extend(
        [
            "",
            "## Total acumulado no manifesto",
            "",
        ]
    )
    if total_counts:
        for class_id, count in sorted(total_counts.items()):
            lines.append(f"- {class_id}: {count}")
    else:
        lines.append("- Nenhuma imagem registrada.")
    lines.extend(
        [
            "",
            "## Fontes usadas nesta execução",
            "",
        ]
    )
    if source_counts:
        for source_name, count in sorted(source_counts.items()):
            lines.append(f"- {source_name}: {count}")
    else:
        lines.append("- Nenhuma fonte com imagem nova.")
    lines.extend(
        [
            "",
            "## Licenças e rastreabilidade",
            "",
            "Cada linha em `wikimedia_capture_manifest.csv` armazena arquivo de origem, página descritiva, autor/crédito, licença e URL da licença quando esses dados existem nos metadados do Commons.",
            "",
            "## Próxima etapa obrigatória",
            "",
            "Criar a planilha de revisão, remover imagens fora de classe, eliminar exemplos ruins e só então promover para `data/curated` antes do treinamento final.",
            "",
        ]
    )
    summary_path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture a starter EcoScan dataset from Wikimedia Commons.")
    parser.add_argument("--source-config", type=Path, default=PROJECT_ROOT / "config" / "web_image_sources.json")
    parser.add_argument("--output-dir", type=Path, default=None, help="Defaults to data/raw from settings.")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "web_capture")
    parser.add_argument("--images-per-class", type=int, default=20)
    parser.add_argument("--thumb-width", type=int, default=768)
    parser.add_argument("--delay-seconds", type=float, default=0.1)
    parser.add_argument("--classes", default="", help="Optional comma-separated class ids to capture.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config()
        output_dir = args.output_dir or config.directories["raw_data"]
        selected_classes = tuple(
            class_id.strip()
            for class_id in str(args.classes).split(",")
            if class_id.strip()
        ) or None
        downloaded = capture_dataset(
            source_config_path=args.source_config,
            output_dir=output_dir,
            report_dir=args.report_dir,
            images_per_class=args.images_per_class,
            thumb_width=args.thumb_width,
            delay_seconds=args.delay_seconds,
            selected_classes=selected_classes,
        )
    except Exception as exc:
        print(f"Erro ao capturar imagens: {exc}")
        return 1

    print(f"Finished. New images captured: {len(downloaded)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
