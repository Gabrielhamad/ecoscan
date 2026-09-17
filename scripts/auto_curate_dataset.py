from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.config import load_config


@dataclass(frozen=True)
class CurationDecision:
    class_id: str
    source_path: str
    target_path: str
    status: str
    reason: str


RULES: dict[str, dict[str, tuple[str, ...]]] = {
    "plastic": {
        "include": ("plastic", "plastico", "pl-stico", "bottle", "botella", "bouteille", "pet", "bag", "container", "packaging", "coca-cola"),
        "reject": ("buddha", "rabbit", "hutch", "cemetery", "granite", "ledger", "dog", "ancienne", "cricket", "lily", "heron", "bus-stop", "as2o3", "colostrum", "aut-tirol"),
    },
    "paper_cardboard": {
        "include": ("paper", "papier", "papel", "papiru", "cardboard", "carton", "corrugated", "box", "boxes", "newspaper", "recycling", "waste", "cup", "bag"),
        "reject": ("token", "historical", "mustard", "sewing", "mattress", "fashion", "parade", "diagram", "building"),
    },
    "metal": {
        "include": ("metal", "aluminium", "aluminum", "can", "cans", "tin", "foil", "scrap", "coca-cola", "drink"),
        "reject": ("train", "dollands", "globe", "atlas", "paraphernalia", "autism", "child"),
    },
    "glass": {
        "include": ("glass", "bottle", "jar", "broken-glass", "vidro", "green-glass", "brown-glass"),
        "reject": ("tv", "window", "almond", "lily", "rose", "beach"),
    },
    "organic": {
        "include": ("food", "waste", "banana", "peel", "compost", "organic", "meal", "plate", "leftover", "fruit", "orange", "pizza", "breakfast", "avocado", "apple", "chicken", "liver", "milano", "finished"),
        "reject": ("poster", "cartoon", "propaganda", "20150916", "anti-food", "library", "sign", "empty-plate", "kibbu"),
    },
    "battery": {
        "include": ("battery", "batteries", "pilas", "lithium", "alkaline", "energizer", "eveready", "cell", "accu", "nicd", "aa-", "aaa"),
        "reject": ("fruit-battery", "fruit-clock", "mandarin", "concert", "drum", "graphite-flow"),
    },
    "electronic": {
        "include": ("electronic", "e-waste", "ewaste", "computer", "circuit", "board", "phone", "cellphone", "monitor", "display", "screen", "keyboard", "desktop", "transistor", "motorola"),
        "reject": ("bench", "library", "water", "glass", "atrapadev", "figurines", "books"),
    },
    "lamp": {
        "include": ("lamp", "bulb", "light", "led", "fluorescent", "cfl", "luz", "lighting"),
        "reject": ("apartment", "cabrils", "bus", "sign", "nuns", "owl", "jack-lemmon", "wood-flooring", "cannon-building"),
    },
    "medicine": {
        "include": ("medicine", "medic", "pill", "tablet", "blister", "pharma", "prescription", "aspirin", "advil", "anastrozole", "atenolol", "oxycodon", "zumenon", "antoren", "rebencoxib"),
        "reject": ("battery", "alkaline", "gold", "cartoix", "abandoned", "porcelain", "aqua-glass", "heroin", "arsenic", "analgesis"),
    },
    "cooking_oil": {
        "include": ("oil", "cooking", "vegetable", "olive", "crisco", "canola", "frying", "peanut", "used-oil", "bottle-of-oil"),
        "reject": ("chipping", "flat-tooth", "siph", "aship", "clock", "sax", "world"),
    },
    "aerosol": {
        "include": ("aerosol", "spray-can", "spray-paint-can", "spray-paint", "deodorant", "hairspray", "body-spray", "insecticide"),
        "reject": ("20170712", "water-san", "man-properly", "best-body-sprays", "amount-of-cologne", "waterloo", "kemp-street", "jwish"),
    },
    "chemical_packaging": {
        "include": ("chemical", "detergent", "bleach", "clorox", "dawn", "tide", "pesticide", "paint-can", "paint-bucket", "cleaning", "disinfectant", "solvent", "hazardous"),
        "reject": ("vase", "bar", "mario", "handwashing", "sports", "wind", "feather", "glass-bottle", "sake", "vodka"),
    },
}


def _matches_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _decide(class_id: str, path: Path) -> tuple[str, str]:
    lowered = path.name.lower()
    if "_taco_" in lowered:
        return "accepted", "taco_annotation_crop"
    rules = RULES.get(class_id, {})
    include_terms = rules.get("include", ())
    reject_terms = rules.get("reject", ())
    if _matches_any(lowered, reject_terms):
        return "rejected", "class_reject_term"
    if _matches_any(lowered, include_terms):
        return "accepted", "class_include_term"
    return "rejected", "missing_strong_class_term"


def _safe_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def auto_curate_dataset(
    *,
    source_dir: Path,
    output_dir: Path,
    report_dir: Path,
    classes: tuple[str, ...],
    extensions: frozenset[str],
    overwrite: bool,
) -> list[CurationDecision]:
    if overwrite and output_dir.exists():
        resolved_output = output_dir.resolve()
        resolved_root = PROJECT_ROOT.resolve()
        if resolved_output == resolved_root or resolved_root not in resolved_output.parents:
            raise RuntimeError(f"Refusing to clear unsafe output path: {output_dir}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    decisions: list[CurationDecision] = []
    for class_id in classes:
        class_dir = source_dir / class_id
        if not class_dir.exists():
            continue
        for source_path in sorted(class_dir.iterdir()):
            if not source_path.is_file() or source_path.suffix.lower() not in extensions:
                continue
            status, reason = _decide(class_id, source_path)
            target_path = output_dir / class_id / source_path.name
            if status == "accepted":
                _safe_copy(source_path, target_path)
            decisions.append(
                CurationDecision(
                    class_id=class_id,
                    source_path=source_path.as_posix(),
                    target_path=target_path.as_posix() if status == "accepted" else "",
                    status=status,
                    reason=reason,
                )
            )

    rows = [decision.__dict__ for decision in decisions]
    (report_dir / "auto_curated_manifest.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    with (report_dir / "auto_curated_manifest.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(CurationDecision.__dataclass_fields__.keys()))
        writer.writeheader()
        writer.writerows(rows)

    accepted_by_class: dict[str, int] = {class_id: 0 for class_id in classes}
    rejected_by_class: dict[str, int] = {class_id: 0 for class_id in classes}
    for decision in decisions:
        if decision.status == "accepted":
            accepted_by_class[decision.class_id] += 1
        else:
            rejected_by_class[decision.class_id] += 1

    lines = [
        "# Curadoria automática EcoScan",
        "",
        "Esta curadoria é reproduzível e conservadora: aceita recortes TACO anotados e imagens com termos fortes da classe no nome do arquivo; rejeita termos visualmente suspeitos.",
        "",
        "| Classe | Aceitas | Rejeitadas |",
        "|---|---:|---:|",
    ]
    for class_id in classes:
        lines.append(f"| {class_id} | {accepted_by_class[class_id]} | {rejected_by_class[class_id]} |")
    lines.append("")
    lines.append("A etapa não substitui revisão humana, mas reduz ruído grosseiro antes do treino.")
    (report_dir / "auto_curated_summary.md").write_text("\n".join(lines), encoding="utf-8")

    return decisions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auto-curate EcoScan dataset with conservative filename/source rules.")
    parser.add_argument("--source", type=Path, default=None, help="Defaults to data/raw.")
    parser.add_argument("--output", type=Path, default=None, help="Defaults to data/curated.")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "dataset_review")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    decisions = auto_curate_dataset(
        source_dir=args.source or config.directories["raw_data"],
        output_dir=args.output or config.directories["curated_data"],
        report_dir=args.report_dir,
        classes=config.classes,
        extensions=config.allowed_extensions,
        overwrite=args.overwrite,
    )
    accepted = sum(1 for decision in decisions if decision.status == "accepted")
    rejected = len(decisions) - accepted
    print("EcoScan auto-curation complete.")
    print(f"Accepted: {accepted}")
    print(f"Rejected: {rejected}")
    print(f"Report: {args.report_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
