from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from ecoscan.config import AppConfig, load_config
from ecoscan.image_processing.validation import ImageValidationError, validate_image_file
from ecoscan.utils.logging_config import configure_logging


LOGGER = logging.getLogger(__name__)
IGNORED_DATASET_FILES = {".gitkeep", ".gitignore", ".ds_store", "thumbs.db"}


@dataclass(frozen=True)
class ImageRecord:
    path: str
    class_id: str
    width: int
    height: int
    mode: str
    image_format: str | None
    file_size_bytes: int
    sha256: str


@dataclass(frozen=True)
class InvalidImageRecord:
    path: str
    class_id: str | None
    reason: str


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _class_for_path(path: Path, dataset_dir: Path) -> str | None:
    relative_parts = path.relative_to(dataset_dir).parts
    if len(relative_parts) < 2:
        return None
    return relative_parts[0]


def _iter_files(dataset_dir: Path) -> Iterable[Path]:
    for path in sorted(dataset_dir.rglob("*")):
        if path.is_file() and path.name.lower() not in IGNORED_DATASET_FILES:
            yield path


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _load_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _write_sample_grid(
    records: list[ImageRecord],
    dataset_root: Path,
    output_path: Path,
    seed: int,
    sample_limit: int,
) -> None:
    if not records:
        return

    rng = random.Random(seed)
    sample = records[:]
    rng.shuffle(sample)
    sample = sample[:sample_limit]

    cell_size = 180
    label_height = 36
    columns = min(4, max(1, len(sample)))
    rows = (len(sample) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * cell_size, rows * (cell_size + label_height)), "white")
    draw = ImageDraw.Draw(canvas)
    font = _load_font(13)

    for index, record in enumerate(sample):
        row = index // columns
        col = index % columns
        x = col * cell_size
        y = row * (cell_size + label_height)
        try:
            with Image.open(dataset_root / record.path) as image:
                image = image.convert("RGB")
                image.thumbnail((cell_size - 12, cell_size - 12))
                offset_x = x + (cell_size - image.width) // 2
                offset_y = y + (cell_size - image.height) // 2
                canvas.paste(image, (offset_x, offset_y))
        except OSError:
            draw.rectangle((x + 8, y + 8, x + cell_size - 8, y + cell_size - 8), outline="red")

        draw.text((x + 8, y + cell_size + 6), record.class_id[:22], fill="black", font=font)

    canvas.save(output_path)


def _write_class_grids(
    records: list[ImageRecord],
    dataset_root: Path,
    report_dir: Path,
    seed: int,
    sample_limit: int,
) -> list[Path]:
    written: list[Path] = []
    records_by_class: dict[str, list[ImageRecord]] = defaultdict(list)
    for record in records:
        records_by_class[record.class_id].append(record)

    for class_id, class_records in sorted(records_by_class.items()):
        output_path = report_dir / f"class_examples_{class_id}.jpg"
        _write_sample_grid(class_records, dataset_root, output_path, seed, sample_limit)
        if output_path.exists():
            written.append(output_path)
    return written


def _write_bar_chart(counts: dict[str, int], output_path: Path) -> None:
    if not counts:
        return

    width = 900
    row_height = 42
    padding = 24
    label_width = 180
    bar_area_width = width - label_width - padding * 3
    height = padding * 2 + len(counts) * row_height
    max_count = max(counts.values()) or 1

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _load_font(16)
    font = _load_font(13)
    draw.text((padding, 8), "Distribuicao de imagens por classe", fill="black", font=title_font)

    for index, (class_id, count) in enumerate(sorted(counts.items())):
        y = padding + 22 + index * row_height
        bar_width = int((count / max_count) * bar_area_width)
        draw.text((padding, y + 6), class_id, fill="black", font=font)
        draw.rectangle(
            (padding + label_width, y, padding + label_width + bar_width, y + 24),
            fill=(44, 125, 160),
        )
        draw.text((padding + label_width + bar_width + 8, y + 5), str(count), fill="black", font=font)

    image.save(output_path)


def _write_resolution_plot(records: list[ImageRecord], output_path: Path) -> None:
    if not records:
        return

    width = 900
    height = 560
    padding = 64
    plot_width = width - padding * 2
    plot_height = height - padding * 2
    max_w = max(record.width for record in records) or 1
    max_h = max(record.height for record in records) or 1

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = _load_font(13)
    title_font = _load_font(16)
    draw.text((padding, 18), "Distribuicao de resolucoes", fill="black", font=title_font)
    draw.rectangle((padding, padding, padding + plot_width, padding + plot_height), outline="black")

    color_by_class: dict[str, tuple[int, int, int]] = {}
    palette = [
        (40, 120, 180),
        (220, 110, 45),
        (90, 150, 85),
        (170, 75, 120),
        (105, 95, 180),
        (180, 160, 55),
        (70, 150, 150),
    ]

    for record in records:
        if record.class_id not in color_by_class:
            color_by_class[record.class_id] = palette[len(color_by_class) % len(palette)]
        x = padding + int((record.width / max_w) * plot_width)
        y = padding + plot_height - int((record.height / max_h) * plot_height)
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color_by_class[record.class_id])

    draw.text((padding, height - 42), f"Largura ate {max_w}px", fill="black", font=font)
    draw.text((padding, height - 24), f"Altura ate {max_h}px", fill="black", font=font)

    legend_x = width - 220
    legend_y = 52
    for class_id, color in sorted(color_by_class.items()):
        draw.rectangle((legend_x, legend_y, legend_x + 14, legend_y + 14), fill=color)
        draw.text((legend_x + 20, legend_y - 1), class_id, fill="black", font=font)
        legend_y += 22

    image.save(output_path)


def _detect_duplicate_groups(records: list[ImageRecord]) -> list[dict[str, list[str] | str]]:
    by_hash: dict[str, list[str]] = defaultdict(list)
    for record in records:
        by_hash[record.sha256].append(record.path)
    return [
        {"sha256": digest, "paths": paths}
        for digest, paths in sorted(by_hash.items())
        if len(paths) > 1
    ]


def analyze_dataset(
    dataset_dir: str | Path,
    *,
    configured_classes: Iterable[str],
    allowed_extensions: set[str] | frozenset[str],
    min_image_size: tuple[int, int],
    min_images_per_class_warning: int,
    imbalance_ratio_warning: float,
) -> dict:
    dataset_root = Path(dataset_dir).resolve()
    configured = tuple(configured_classes)
    if not dataset_root.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_root}")
    if not dataset_root.is_dir():
        raise NotADirectoryError(f"Dataset path is not a directory: {dataset_root}")

    records: list[ImageRecord] = []
    invalid_records: list[InvalidImageRecord] = []
    unsupported_files = 0

    for path in _iter_files(dataset_root):
        class_id = _class_for_path(path, dataset_root)
        suffix = path.suffix.lower()
        if suffix not in allowed_extensions:
            unsupported_files += 1
            invalid_records.append(
                InvalidImageRecord(
                    path=_relative(path, dataset_root),
                    class_id=class_id,
                    reason=f"unsupported format: {suffix or 'no extension'}",
                )
            )
            continue

        try:
            info = validate_image_file(
                path,
                allowed_extensions=allowed_extensions,
                min_size=min_image_size,
            )
            records.append(
                ImageRecord(
                    path=_relative(path, dataset_root),
                    class_id=class_id or "__unlabeled__",
                    width=info.width,
                    height=info.height,
                    mode=info.mode,
                    image_format=info.format,
                    file_size_bytes=path.stat().st_size,
                    sha256=_hash_file(path),
                )
            )
        except ImageValidationError as exc:
            invalid_records.append(
                InvalidImageRecord(path=_relative(path, dataset_root), class_id=class_id, reason=str(exc))
            )

    class_counts = Counter(record.class_id for record in records)
    present_classes = sorted(class_counts)
    missing_classes = sorted(set(configured) - set(present_classes))
    unknown_classes = sorted(set(present_classes) - set(configured) - {"__unlabeled__"})
    duplicate_groups = _detect_duplicate_groups(records)

    resolution_counts = Counter(f"{record.width}x{record.height}" for record in records)
    small_images = [
        record for record in records
        if record.width < min_image_size[0] or record.height < min_image_size[1]
    ]

    potential_issues: list[str] = []
    if not records:
        potential_issues.append("Nenhuma imagem valida encontrada.")
    for class_id in missing_classes:
        potential_issues.append(f"Classe configurada sem imagens validas: {class_id}.")
    for class_id in unknown_classes:
        potential_issues.append(f"Classe presente no dataset mas ausente da configuracao: {class_id}.")
    if "__unlabeled__" in present_classes:
        potential_issues.append("Ha imagens diretamente na raiz do dataset, sem pasta de classe.")
    for class_id, count in sorted(class_counts.items()):
        if class_id != "__unlabeled__" and count < min_images_per_class_warning:
            potential_issues.append(
                f"Poucas imagens na classe {class_id}: {count} "
                f"(referencia de alerta: {min_images_per_class_warning})."
            )
    non_zero_counts = [count for class_id, count in class_counts.items() if class_id != "__unlabeled__" and count > 0]
    if len(non_zero_counts) >= 2:
        ratio = max(non_zero_counts) / min(non_zero_counts)
        if ratio >= imbalance_ratio_warning:
            potential_issues.append(
                f"Possivel desbalanceamento entre classes: razao {ratio:.2f} "
                f"(limiar: {imbalance_ratio_warning:.2f})."
            )
    if duplicate_groups:
        potential_issues.append(f"Encontrados {len(duplicate_groups)} grupos de duplicatas exatas por SHA-256.")
    if unsupported_files:
        potential_issues.append(f"Encontrados {unsupported_files} arquivos com formato nao suportado.")
    if small_images:
        potential_issues.append(f"Encontradas {len(small_images)} imagens abaixo do tamanho minimo configurado.")

    total_pixels = [record.width * record.height for record in records]
    summary = {
        "dataset_dir": str(dataset_root),
        "configured_classes": list(configured),
        "present_classes": present_classes,
        "missing_classes": missing_classes,
        "unknown_classes": unknown_classes,
        "total_valid_images": len(records),
        "total_invalid_images": len(invalid_records),
        "class_counts": dict(sorted(class_counts.items())),
        "resolution_counts": dict(sorted(resolution_counts.items())),
        "resolution_stats": {
            "min_width": min((record.width for record in records), default=0),
            "max_width": max((record.width for record in records), default=0),
            "min_height": min((record.height for record in records), default=0),
            "max_height": max((record.height for record in records), default=0),
            "min_pixels": min(total_pixels, default=0),
            "max_pixels": max(total_pixels, default=0),
        },
        "invalid_images": [asdict(record) for record in invalid_records],
        "duplicates_exact": duplicate_groups,
        "potential_issues": potential_issues,
        "notes": [
            "Duplicatas quase identicas ainda exigem analise perceptual/manual em fase posterior.",
            "A avaliacao de iluminacao, fundo e variedade visual depende de amostragem visual do grupo.",
        ],
        "records": [asdict(record) for record in records],
    }
    return summary


def write_dataset_report(
    analysis: dict,
    output_dir: str | Path,
    *,
    sample_limit: int,
    seed: int,
) -> list[Path]:
    report_dir = Path(output_dir).resolve()
    report_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    json_path = report_dir / "dataset_analysis.json"
    _write_json(json_path, analysis)
    written.append(json_path)

    class_rows = [
        {"class_id": class_id, "image_count": count}
        for class_id, count in analysis["class_counts"].items()
    ]
    class_csv = report_dir / "class_distribution.csv"
    _write_csv(class_csv, class_rows, ["class_id", "image_count"])
    written.append(class_csv)

    resolution_rows = [
        {"resolution": resolution, "image_count": count}
        for resolution, count in analysis["resolution_counts"].items()
    ]
    resolution_csv = report_dir / "resolution_distribution.csv"
    _write_csv(resolution_csv, resolution_rows, ["resolution", "image_count"])
    written.append(resolution_csv)

    invalid_csv = report_dir / "invalid_images.csv"
    _write_csv(invalid_csv, analysis["invalid_images"], ["path", "class_id", "reason"])
    written.append(invalid_csv)

    issues_path = report_dir / "potential_issues.txt"
    issues = analysis["potential_issues"] or ["Nenhum problema automatico identificado."]
    issues_path.write_text("\n".join(issues) + "\n", encoding="utf-8")
    written.append(issues_path)

    records = [ImageRecord(**record) for record in analysis["records"]]
    dataset_root = Path(analysis["dataset_dir"]).resolve()
    sample_grid = report_dir / "random_examples.jpg"
    _write_sample_grid(records, dataset_root, sample_grid, seed, sample_limit)
    if sample_grid.exists():
        written.append(sample_grid)
    written.extend(_write_class_grids(records, dataset_root, report_dir, seed, sample_limit))

    bar_chart = report_dir / "class_distribution.png"
    _write_bar_chart(analysis["class_counts"], bar_chart)
    if bar_chart.exists():
        written.append(bar_chart)

    resolution_plot = report_dir / "resolution_distribution.png"
    _write_resolution_plot(records, resolution_plot)
    if resolution_plot.exists():
        written.append(resolution_plot)

    return written


def analyze_from_config(config: AppConfig, dataset_dir: Path | None, output_dir: Path | None, sample_limit: int) -> dict:
    selected_dataset_dir = dataset_dir or config.directories["raw_data"]
    selected_output_dir = output_dir or config.directories["reports"] / "dataset_analysis"

    analysis = analyze_dataset(
        selected_dataset_dir,
        configured_classes=config.classes,
        allowed_extensions=config.allowed_extensions,
        min_image_size=config.min_image_size,
        min_images_per_class_warning=config.min_images_per_class_warning,
        imbalance_ratio_warning=config.imbalance_ratio_warning,
    )
    written = write_dataset_report(
        analysis,
        selected_output_dir,
        sample_limit=sample_limit,
        seed=config.random_seed,
    )
    LOGGER.info("Dataset analysis written to %s", selected_output_dir)
    analysis["report_files"] = [str(path) for path in written]
    return analysis


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze an EcoScan image dataset.")
    parser.add_argument("--config", type=Path, default=None, help="Path to config/settings.json.")
    parser.add_argument("--dataset", type=Path, default=None, help="Dataset root. Defaults to data/raw.")
    parser.add_argument("--output", type=Path, default=None, help="Report output directory.")
    parser.add_argument("--sample-limit", type=int, default=12, help="Number of random examples in the grid.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        configure_logging(config.directories["logs"])
        analysis = analyze_from_config(config, args.dataset, args.output, args.sample_limit)
    except Exception as exc:
        LOGGER.error("Dataset analysis failed: %s", exc)
        print(f"Erro ao analisar dataset: {exc}")
        return 1

    print("EcoScan dataset analysis complete.")
    print(f"Valid images: {analysis['total_valid_images']}")
    print(f"Invalid images: {analysis['total_invalid_images']}")
    if analysis["potential_issues"]:
        print("Potential issues:")
        for issue in analysis["potential_issues"]:
            print(f"- {issue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
