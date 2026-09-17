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


OPENVERSE_API = "https://api.openverse.org/v1/images/"
USER_AGENT = "EcoScanOpenverseDatasetBuilder/0.1 (academic local dataset builder)"
SUPPORTED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
}
SUPPORTED_URL_SUFFIXES = {
    ".jpg": ".jpg",
    ".jpeg": ".jpg",
    ".png": ".png",
}


@dataclass(frozen=True)
class OpenverseImage:
    class_id: str
    local_path: str
    title: str
    query: str
    image_url: str
    thumbnail_url: str
    landing_url: str
    provider: str
    source: str
    license: str
    license_url: str
    creator: str
    width: int
    height: int
    sha256: str


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    encoded = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{encoded}",
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _download_bytes(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        content_type = str(response.headers.get("Content-Type", "")).split(";")[0].strip().lower()
        return response.read(), content_type


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sanitize_filename(value: str) -> str:
    value = urllib.parse.unquote(value)
    value = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", value)
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value[:64] or "openverse-image"


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _extension_for(download_url: str, content_type: str) -> str | None:
    if content_type in SUPPORTED_CONTENT_TYPES:
        return SUPPORTED_CONTENT_TYPES[content_type]
    suffix = Path(urllib.parse.urlparse(download_url).path).suffix.lower()
    return SUPPORTED_URL_SUFFIXES.get(suffix)


def _normalize_queries(raw_classes: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    normalized: dict[str, tuple[str, ...]] = {}
    for class_id, value in raw_classes.items():
        if isinstance(value, list):
            queries = tuple(str(item).strip() for item in value if str(item).strip())
        elif isinstance(value, dict):
            values = value.get("queries") or value.get("search_terms") or []
            queries = tuple(str(item).strip() for item in values if str(item).strip())
        else:
            raise ValueError(f"Invalid Openverse source configuration for class: {class_id}")
        if not queries:
            raise ValueError(f"No Openverse queries configured for class: {class_id}")
        normalized[str(class_id)] = queries
    return normalized


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


def _image_from_row(row: dict[str, Any]) -> OpenverseImage | None:
    try:
        return OpenverseImage(
            class_id=str(row.get("class_id", "")),
            local_path=str(row.get("local_path", "")),
            title=str(row.get("title", "")),
            query=str(row.get("query", "")),
            image_url=str(row.get("image_url", "")),
            thumbnail_url=str(row.get("thumbnail_url", "")),
            landing_url=str(row.get("landing_url", "")),
            provider=str(row.get("provider", "")),
            source=str(row.get("source", "")),
            license=str(row.get("license", "")),
            license_url=str(row.get("license_url", "")),
            creator=str(row.get("creator", "")),
            width=int(row.get("width", 0) or 0),
            height=int(row.get("height", 0) or 0),
            sha256=str(row.get("sha256", "")),
        )
    except (TypeError, ValueError):
        return None


def _load_existing_manifest(report_dir: Path) -> list[OpenverseImage]:
    manifest_path = report_dir / "openverse_capture_manifest.json"
    if not manifest_path.exists():
        return []
    try:
        raw_rows = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw_rows, list):
        return []
    rows: list[OpenverseImage] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        image = _image_from_row(row)
        if image and _manifest_file_exists(image.local_path):
            rows.append(image)
    return rows


def _manifest_file_exists(local_path: str) -> bool:
    path = Path(local_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.exists()


def _merge_rows(rows: list[OpenverseImage]) -> list[OpenverseImage]:
    merged: list[OpenverseImage] = []
    seen: set[str] = set()
    for row in rows:
        key = row.sha256 or row.image_url or f"{row.class_id}:{row.title}:{row.local_path}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
    return merged


def _openverse_results(
    *,
    api_url: str,
    query: str,
    license_type: str,
    page_size: int,
    page_limit: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in range(1, page_limit + 1):
        params = {
            "q": query,
            "format": "json",
            "page": page,
            "page_size": page_size,
            "license_type": license_type,
            "mature": "false",
            "filter_dead": "true",
        }
        data = _request_json(api_url, params)
        results = data.get("results", [])
        if not isinstance(results, list) or not results:
            break
        rows.extend(item for item in results if isinstance(item, dict))
        page_count = int(data.get("page_count", page) or page)
        if page >= page_count:
            break
        time.sleep(0.5)
    return rows


def _result_text(result: dict[str, Any]) -> str:
    tag_values = []
    for tag in result.get("tags", []) or []:
        if isinstance(tag, dict):
            tag_values.append(str(tag.get("name", "")))
        else:
            tag_values.append(str(tag))
    values = [
        str(result.get("title") or ""),
        str(result.get("url") or ""),
        str(result.get("thumbnail") or ""),
        str(result.get("foreign_landing_url") or ""),
        " ".join(tag_values),
    ]
    return " ".join(values).lower()


def _terms_for_class(term_map: dict[str, tuple[str, ...]], class_id: str) -> tuple[str, ...]:
    return (*term_map.get("_all", ()), *term_map.get(class_id, ()))


def _result_matches_class(
    result: dict[str, Any],
    include_terms: tuple[str, ...],
    reject_terms: tuple[str, ...] = (),
) -> bool:
    text = _result_text(result)
    if any(term.lower() in text for term in reject_terms):
        return False
    if not include_terms:
        return True
    return any(term.lower() in text for term in include_terms)


def write_manifest(
    existing_manifest: list[OpenverseImage],
    downloaded: list[OpenverseImage],
    report_dir: Path,
    source_config: dict[str, Any],
) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    all_rows = _merge_rows([*existing_manifest, *downloaded])
    rows = [row.__dict__ for row in all_rows]

    json_path = report_dir / "openverse_capture_manifest.json"
    csv_path = report_dir / "openverse_capture_manifest.csv"
    summary_path = report_dir / "openverse_capture_summary.md"

    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    fieldnames = [
        "class_id",
        "local_path",
        "title",
        "query",
        "image_url",
        "thumbnail_url",
        "landing_url",
        "provider",
        "source",
        "license",
        "license_url",
        "creator",
        "width",
        "height",
        "sha256",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    total_counts: dict[str, int] = {}
    new_counts: dict[str, int] = {}
    query_counts: dict[str, int] = {}
    for image in all_rows:
        total_counts[image.class_id] = total_counts.get(image.class_id, 0) + 1
    for image in downloaded:
        new_counts[image.class_id] = new_counts.get(image.class_id, 0) + 1
        query_counts[image.query] = query_counts.get(image.query, 0) + 1

    provider = source_config.get("provider", "Openverse")
    provider_url = source_config.get("provider_url", "https://openverse.org/")
    lines = [
        "# Captura Openverse do dataset EcoScan",
        "",
        f"Fonte complementar: [{provider}]({provider_url}).",
        "",
        "Openverse agrega metadados de mídia aberta hospedada por terceiros. O manifesto mantém licença e página de origem, mas a curadoria visual e a verificação de licença continuam obrigatórias antes do treino final.",
        "",
        "## Imagens novas nesta execução",
        "",
    ]
    if new_counts:
        for class_id, count in sorted(new_counts.items()):
            lines.append(f"- {class_id}: {count}")
    else:
        lines.append("- Nenhuma imagem nova capturada.")
    lines.extend(["", "## Total acumulado no manifesto", ""])
    if total_counts:
        for class_id, count in sorted(total_counts.items()):
            lines.append(f"- {class_id}: {count}")
    else:
        lines.append("- Nenhuma imagem registrada.")
    lines.extend(["", "## Consultas usadas nesta execução", ""])
    if query_counts:
        for query, count in sorted(query_counts.items()):
            lines.append(f"- {query}: {count}")
    else:
        lines.append("- Nenhuma consulta com imagem nova.")
    lines.extend(
        [
            "",
            "## Próxima etapa obrigatória",
            "",
            "Revisar cada arquivo em `reports/dataset_review/review_sheet.csv`, rejeitar imagens fora de classe e promover apenas exemplos aprovados para `data/curated`.",
            "",
        ]
    )
    summary_path.write_text("\n".join(lines), encoding="utf-8")


def capture_dataset(
    *,
    source_config_path: Path,
    output_dir: Path,
    report_dir: Path,
    images_per_class: int,
    page_size: int,
    page_limit: int,
    delay_seconds: float,
    selected_classes: tuple[str, ...] | None = None,
    download_field: str = "thumbnail",
) -> list[OpenverseImage]:
    source_config = _read_json(source_config_path)
    api_url = str(source_config.get("api_url", OPENVERSE_API))
    license_type = str(source_config.get("license_type", "commercial,modification"))
    queries_by_class = _normalize_queries(source_config["classes"])
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
    selected_class_set = set(selected_classes or ())

    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    existing_manifest = _load_existing_manifest(report_dir)
    downloaded: list[OpenverseImage] = []
    seen_urls = {
        url
        for row in existing_manifest
        for url in (row.image_url, row.thumbnail_url, row.landing_url)
        if url
    }
    seen_hashes = {row.sha256 for row in existing_manifest if row.sha256}
    seen_hashes.update(_existing_file_hashes(output_dir))

    for class_id, queries in queries_by_class.items():
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

        for query in queries:
            if needed <= 0:
                break
            try:
                results = _openverse_results(
                    api_url=api_url,
                    query=query,
                    license_type=license_type,
                    page_size=page_size,
                    page_limit=page_limit,
                )
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                print(f"  {query}: failed to collect results: {exc}")
                continue

            for result in results:
                if needed <= 0:
                    break
                if not _result_matches_class(
                    result,
                    title_filters.get(class_id, ()),
                    _terms_for_class(reject_filters, class_id),
                ):
                    continue
                image_url = str(result.get("url") or "")
                thumbnail_url = str(result.get("thumbnail") or "")
                landing_url = str(result.get("foreign_landing_url") or result.get("foreign_identifier") or "")
                download_url = thumbnail_url if download_field == "thumbnail" else image_url
                if not download_url:
                    download_url = image_url or thumbnail_url
                if not download_url or download_url in seen_urls or landing_url in seen_urls:
                    continue

                try:
                    image_bytes, content_type = _download_bytes(download_url)
                except urllib.error.HTTPError as exc:
                    if exc.code == 429:
                        print(f"  {query}: rate limited by image host; skipping query.")
                        break
                    if exc.code == 424 and download_url == thumbnail_url and image_url and image_url != thumbnail_url:
                        try:
                            image_bytes, content_type = _download_bytes(image_url)
                            download_url = image_url
                        except (urllib.error.URLError, TimeoutError) as fallback_exc:
                            print(f"  {thumbnail_url}: thumbnail failed and original failed: {fallback_exc}")
                            continue
                    else:
                        print(f"  {download_url}: download failed: {exc}")
                        continue
                except (urllib.error.URLError, TimeoutError) as exc:
                    print(f"  {download_url}: download failed: {exc}")
                    continue

                extension = _extension_for(download_url, content_type)
                if extension is None:
                    continue
                digest = _sha256(image_bytes)
                if digest in seen_hashes:
                    continue

                title = str(result.get("title") or query)
                filename = f"{class_id}_{sequence:04d}_{_sanitize_filename(title)}{extension}"
                local_path = class_dir / filename
                local_path.write_bytes(image_bytes)

                downloaded.append(
                    OpenverseImage(
                        class_id=class_id,
                        local_path=_safe_relative(local_path, PROJECT_ROOT),
                        title=title,
                        query=query,
                        image_url=image_url,
                        thumbnail_url=thumbnail_url,
                        landing_url=landing_url,
                        provider=str(result.get("provider") or ""),
                        source=str(result.get("source") or ""),
                        license=str(result.get("license") or ""),
                        license_url=str(result.get("license_url") or ""),
                        creator=str(result.get("creator") or ""),
                        width=int(result.get("width") or 0),
                        height=int(result.get("height") or 0),
                        sha256=digest,
                    )
                )
                seen_urls.update(url for url in (image_url, thumbnail_url, landing_url) if url)
                seen_hashes.add(digest)
                sequence += 1
                needed -= 1
                print(f"  saved {local_path.name}")
                write_manifest(existing_manifest, downloaded, report_dir, source_config)
                time.sleep(delay_seconds)

        if needed > 0:
            print(f"{class_id}: still missing {needed} image(s); review queries or add another source.")
        write_manifest(existing_manifest, downloaded, report_dir, source_config)

    write_manifest(existing_manifest, downloaded, report_dir, source_config)
    return downloaded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture an EcoScan dataset from Openverse.")
    parser.add_argument("--source-config", type=Path, default=PROJECT_ROOT / "config" / "openverse_image_sources.json")
    parser.add_argument("--output-dir", type=Path, default=None, help="Defaults to data/raw from settings.")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "openverse_capture")
    parser.add_argument("--images-per-class", type=int, default=50)
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--page-limit", type=int, default=2)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--classes", default="", help="Optional comma-separated class ids to capture.")
    parser.add_argument("--download-field", choices=["thumbnail", "url"], default="thumbnail")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config()
        selected_classes = tuple(
            class_id.strip()
            for class_id in str(args.classes).split(",")
            if class_id.strip()
        ) or None
        downloaded = capture_dataset(
            source_config_path=args.source_config,
            output_dir=args.output_dir or config.directories["raw_data"],
            report_dir=args.report_dir,
            images_per_class=args.images_per_class,
            page_size=args.page_size,
            page_limit=args.page_limit,
            delay_seconds=args.delay_seconds,
            selected_classes=selected_classes,
            download_field=args.download_field,
        )
    except Exception as exc:
        print(f"Erro ao capturar imagens do Openverse: {exc}")
        return 1

    print(f"Finished. New images captured: {len(downloaded)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
