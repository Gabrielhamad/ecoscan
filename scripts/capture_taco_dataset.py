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
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError


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


USER_AGENT = "EcoScanTacoDatasetBuilder/0.1 (academic local dataset builder)"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


@dataclass(frozen=True)
class TacoCrop:
    class_id: str
    local_path: str
    taco_image_id: int
    taco_annotation_id: int
    taco_category: str
    source_file_name: str
    source_url: str
    bbox_original: list[float]
    crop_box: list[int]
    width: int
    height: int
    sha256: str


def _read_json(path_or_url: str | Path) -> dict[str, Any]:
    value = str(path_or_url)
    if value.startswith(("http://", "https://")):
        request = urllib.request.Request(value, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    return json.loads(Path(path_or_url).read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _sanitize_filename(value: str) -> str:
    value = urllib.parse.unquote(value)
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value[:48] or "taco"


def _existing_count(output_dir: Path, class_id: str) -> int:
    class_dir = output_dir / class_id
    if not class_dir.exists():
        return 0
    return sum(1 for path in class_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)


def _existing_file_hashes(output_dir: Path) -> set[str]:
    hashes: set[str] = set()
    if not output_dir.exists():
        return hashes
    for path in output_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        try:
            hashes.add(_sha256(path.read_bytes()))
        except OSError:
            continue
    return hashes


def _crop_from_row(row: dict[str, Any]) -> TacoCrop | None:
    try:
        return TacoCrop(
            class_id=str(row.get("class_id", "")),
            local_path=str(row.get("local_path", "")),
            taco_image_id=int(row.get("taco_image_id", 0)),
            taco_annotation_id=int(row.get("taco_annotation_id", 0)),
            taco_category=str(row.get("taco_category", "")),
            source_file_name=str(row.get("source_file_name", "")),
            source_url=str(row.get("source_url", "")),
            bbox_original=[float(value) for value in row.get("bbox_original", [])],
            crop_box=[int(value) for value in row.get("crop_box", [])],
            width=int(row.get("width", 0)),
            height=int(row.get("height", 0)),
            sha256=str(row.get("sha256", "")),
        )
    except (TypeError, ValueError):
        return None


def _manifest_file_exists(local_path: str) -> bool:
    path = Path(local_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.exists()


def _load_existing_manifest(report_dir: Path) -> list[TacoCrop]:
    manifest_path = report_dir / "taco_capture_manifest.json"
    if not manifest_path.exists():
        return []
    try:
        raw_rows = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows: list[TacoCrop] = []
    for row in raw_rows if isinstance(raw_rows, list) else []:
        if not isinstance(row, dict):
            continue
        crop = _crop_from_row(row)
        if crop and _manifest_file_exists(crop.local_path):
            rows.append(crop)
    return rows


def _category_to_class(source_config: dict[str, Any]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for class_id, categories in dict(source_config.get("classes", {})).items():
        if not isinstance(categories, list):
            continue
        for category in categories:
            mapped[str(category)] = str(class_id)
    return mapped


def _select_source_url(image_row: dict[str, Any]) -> str:
    return str(image_row.get("flickr_640_url") or image_row.get("flickr_url") or "")


def _download_image(url: str) -> Image.Image:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read()
    image = Image.open(BytesIO(data))
    image.load()
    return image.convert("RGB")


def _scaled_crop_box(
    bbox: list[float],
    *,
    source_width: int,
    source_height: int,
    actual_width: int,
    actual_height: int,
    margin_ratio: float,
) -> tuple[int, int, int, int]:
    if len(bbox) != 4 or source_width <= 0 or source_height <= 0:
        return (0, 0, 0, 0)

    x, y, width, height = bbox
    scale_x = actual_width / source_width
    scale_y = actual_height / source_height
    margin_x = width * margin_ratio
    margin_y = height * margin_ratio

    left = max(0, round((x - margin_x) * scale_x))
    top = max(0, round((y - margin_y) * scale_y))
    right = min(actual_width, round((x + width + margin_x) * scale_x))
    bottom = min(actual_height, round((y + height + margin_y) * scale_y))
    return (left, top, right, bottom)


def _is_large_enough(box: tuple[int, int, int, int], min_crop_size: int) -> bool:
    left, top, right, bottom = box
    return (right - left) >= min_crop_size and (bottom - top) >= min_crop_size


def _merge_rows(rows: list[TacoCrop]) -> list[TacoCrop]:
    merged: list[TacoCrop] = []
    seen: set[str] = set()
    for row in rows:
        key = f"{row.taco_annotation_id}:{row.sha256}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
    return merged


def write_manifest(
    existing_manifest: list[TacoCrop],
    downloaded: list[TacoCrop],
    report_dir: Path,
    source_config: dict[str, Any],
) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    all_rows = _merge_rows([*existing_manifest, *downloaded])
    rows = [row.__dict__ for row in all_rows]

    json_path = report_dir / "taco_capture_manifest.json"
    csv_path = report_dir / "taco_capture_manifest.csv"
    summary_path = report_dir / "taco_capture_summary.md"

    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(TacoCrop.__dataclass_fields__.keys()))
        writer.writeheader()
        writer.writerows(rows)

    total_counts: dict[str, int] = {}
    new_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for row in all_rows:
        total_counts[row.class_id] = total_counts.get(row.class_id, 0) + 1
    for row in downloaded:
        new_counts[row.class_id] = new_counts.get(row.class_id, 0) + 1
        category_counts[row.taco_category] = category_counts.get(row.taco_category, 0) + 1

    provider = str(source_config.get("provider", "TACO"))
    provider_url = str(source_config.get("provider_url", "https://tacodataset.org/"))
    repository_url = str(source_config.get("repository_url", "https://github.com/pedropro/TACO"))
    citation = str(source_config.get("citation", ""))
    license_name = str(source_config.get("license", ""))
    license_url = str(source_config.get("license_url", ""))

    lines = [
        "# Captura TACO do dataset EcoScan",
        "",
        f"Fonte: [{provider}]({provider_url}).",
        f"Repositório/anotações: {repository_url}.",
        "",
        "O importador usa as anotações COCO do TACO para recortar objetos individuais, evitando treinar a baseline com o cenário inteiro quando a imagem possui múltiplos resíduos.",
        "",
        "## Licença e citação",
        "",
        f"- Licença declarada no projeto: [{license_name}]({license_url})." if license_name else "- Licença: revisar metadados do projeto antes de redistribuir.",
        f"- Citação: {citation}" if citation else "- Citação: revisar documentação oficial do TACO.",
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

    lines.extend(["", "## Categorias TACO usadas nesta execução", ""])
    if category_counts:
        for category, count in sorted(category_counts.items()):
            lines.append(f"- {category}: {count}")
    else:
        lines.append("- Nenhuma categoria nova.")

    lines.extend(
        [
            "",
            "## Próxima etapa obrigatória",
            "",
            "Rodar `scripts\\prepare_dataset_images.py` para aplicar filtragem, segmentação e validação de qualidade nos recortes antes do treino.",
            "",
        ]
    )
    summary_path.write_text("\n".join(lines), encoding="utf-8")


def capture_taco_dataset(
    *,
    source_config_path: Path,
    output_dir: Path,
    report_dir: Path,
    images_per_class: int,
    selected_classes: tuple[str, ...] | None = None,
    margin_ratio: float = 0.12,
    min_crop_size: int = 64,
    delay_seconds: float = 0.2,
) -> list[TacoCrop]:
    source_config = _read_json(source_config_path)
    annotations_url = str(source_config["annotations_url"])
    annotations_data = _read_json(annotations_url)
    category_map = _category_to_class(source_config)
    selected_class_set = set(selected_classes or ())

    categories = {int(row["id"]): str(row["name"]) for row in annotations_data.get("categories", [])}
    images = {int(row["id"]): row for row in annotations_data.get("images", [])}
    annotations = list(annotations_data.get("annotations", []))

    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    existing_manifest = _load_existing_manifest(report_dir)
    seen_annotations = {row.taco_annotation_id for row in existing_manifest}
    seen_hashes = {row.sha256 for row in existing_manifest if row.sha256}
    seen_hashes.update(_existing_file_hashes(output_dir))

    remaining_by_class: dict[str, int] = {}
    sequence_by_class: dict[str, int] = {}
    for class_id in sorted(set(category_map.values())):
        if selected_class_set and class_id not in selected_class_set:
            continue
        already_present = _existing_count(output_dir, class_id)
        remaining_by_class[class_id] = max(0, images_per_class - already_present)
        sequence_by_class[class_id] = already_present + 1
        if remaining_by_class[class_id] == 0:
            print(f"{class_id}: already has {already_present} images; skipping.")
        else:
            print(f"{class_id}: collecting up to {remaining_by_class[class_id]} TACO crop(s).")

    downloaded: list[TacoCrop] = []
    image_cache: dict[int, Image.Image] = {}

    for annotation in annotations:
        annotation_id = int(annotation.get("id", 0) or 0)
        if annotation_id in seen_annotations:
            continue

        category_name = categories.get(int(annotation.get("category_id", -1)), "")
        class_id = category_map.get(category_name)
        if not class_id or (selected_class_set and class_id not in selected_class_set):
            continue
        if remaining_by_class.get(class_id, 0) <= 0:
            continue

        image_id = int(annotation.get("image_id", -1))
        image_row = images.get(image_id)
        if not isinstance(image_row, dict):
            continue

        source_url = _select_source_url(image_row)
        if not source_url:
            continue

        try:
            image = image_cache.get(image_id)
            if image is None:
                image = _download_image(source_url)
                image_cache[image_id] = image
                time.sleep(delay_seconds)
        except (urllib.error.URLError, TimeoutError, UnidentifiedImageError, OSError) as exc:
            print(f"  {source_url}: download failed: {exc}")
            continue

        bbox = [float(value) for value in annotation.get("bbox", [])]
        crop_box = _scaled_crop_box(
            bbox,
            source_width=int(image_row.get("width", 0) or 0),
            source_height=int(image_row.get("height", 0) or 0),
            actual_width=image.width,
            actual_height=image.height,
            margin_ratio=margin_ratio,
        )
        if not _is_large_enough(crop_box, min_crop_size):
            continue

        crop = image.crop(crop_box)
        buffer = BytesIO()
        crop.save(buffer, format="JPEG", quality=92, optimize=True)
        image_bytes = buffer.getvalue()
        digest = _sha256(image_bytes)
        if digest in seen_hashes:
            continue

        class_dir = output_dir / class_id
        class_dir.mkdir(parents=True, exist_ok=True)
        sequence = sequence_by_class[class_id]
        filename = f"{class_id}_{sequence:04d}_taco_{image_id}_{annotation_id}_{_sanitize_filename(category_name)}.jpg"
        local_path = class_dir / filename
        local_path.write_bytes(image_bytes)

        row = TacoCrop(
            class_id=class_id,
            local_path=_safe_relative(local_path, PROJECT_ROOT),
            taco_image_id=image_id,
            taco_annotation_id=annotation_id,
            taco_category=category_name,
            source_file_name=str(image_row.get("file_name", "")),
            source_url=source_url,
            bbox_original=bbox,
            crop_box=list(crop_box),
            width=crop.width,
            height=crop.height,
            sha256=digest,
        )
        downloaded.append(row)
        seen_annotations.add(annotation_id)
        seen_hashes.add(digest)
        sequence_by_class[class_id] += 1
        remaining_by_class[class_id] -= 1
        print(f"  saved {local_path.name}")
        write_manifest(existing_manifest, downloaded, report_dir, source_config)

        if all(remaining <= 0 for remaining in remaining_by_class.values()):
            break

    for class_id, remaining in sorted(remaining_by_class.items()):
        if remaining > 0:
            print(f"{class_id}: still missing {remaining} image(s); TACO has no more mapped crops.")

    write_manifest(existing_manifest, downloaded, report_dir, source_config)
    return downloaded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture object crops from the TACO waste dataset.")
    parser.add_argument("--source-config", type=Path, default=PROJECT_ROOT / "config" / "taco_category_map.json")
    parser.add_argument("--output-dir", type=Path, default=None, help="Defaults to data/raw from settings.")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "taco_capture")
    parser.add_argument("--images-per-class", type=int, default=50)
    parser.add_argument("--classes", default="", help="Optional comma-separated EcoScan class ids to capture.")
    parser.add_argument("--margin-ratio", type=float, default=0.12)
    parser.add_argument("--min-crop-size", type=int, default=64)
    parser.add_argument("--delay-seconds", type=float, default=0.2)
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
        downloaded = capture_taco_dataset(
            source_config_path=args.source_config,
            output_dir=args.output_dir or config.directories["raw_data"],
            report_dir=args.report_dir,
            images_per_class=args.images_per_class,
            selected_classes=selected_classes,
            margin_ratio=args.margin_ratio,
            min_crop_size=args.min_crop_size,
            delay_seconds=args.delay_seconds,
        )
    except Exception as exc:
        print(f"Erro ao capturar imagens do TACO: {exc}")
        return 1

    print(f"Finished. New TACO crops captured: {len(downloaded)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
