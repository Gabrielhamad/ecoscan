"""Run the controlled EcoScan image-preparation and recognition training cycle."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from ecoscan.config import load_config
from ecoscan.app.pipeline import default_processing_options
from ecoscan.image_processing.contracts import processing_contract, write_model_contract
from ecoscan.services.dataset_preparation import prepare_dataset_images
from ecoscan.services.dataset_split import split_dataset
from train_visual_svm import main as train_visual_svm


def _image_count(path: Path, classes: tuple[str, ...], extensions: frozenset[str]) -> dict[str, int]:
    counts = {class_id: 0 for class_id in classes}
    for class_id in classes:
        class_dir = path / class_id
        if class_dir.exists():
            counts[class_id] = sum(
                1 for item in class_dir.iterdir()
                if item.is_file() and item.suffix.lower() in extensions
            )
    return counts


def _has_files(path: Path) -> bool:
    return path.exists() and any(item.is_file() for item in path.rglob("*"))


def _guard_rebuild(config, overwrite: bool) -> None:
    if overwrite:
        return
    existing = [
        config.directories["processed_data"],
        config.directories["train_data"],
        config.directories["validation_data"],
        config.directories["test_data"],
    ]
    if any(_has_files(path) for path in existing):
        raise RuntimeError(
            "Já existem imagens preparadas ou divididas. Use --overwrite somente "
            "depois de confirmar o backup/manifesto da rodada anterior."
        )


def _guard_candidate_output(config, output_model: Path) -> None:
    active_paths = {
        config.directories["models"] / "vision_svm_classifier.joblib",
        config.directories["models"] / "vision_classifier.npz",
        config.directories["models"] / "baseline_classifier.json",
        config.project_root / str(config.model.get("output_path", "models/ecoscan_transfer.keras")),
    }
    if output_model.resolve() in {path.resolve() for path in active_paths}:
        raise ValueError("O ciclo só pode salvar um candidato; o caminho do modelo ativo é protegido.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare, split and select a supervised visual model candidate for EcoScan."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Curated dataset source. Defaults to data/curated; raw is intentionally not the default.",
    )
    parser.add_argument(
        "--output-model",
        type=Path,
        default=PROJECT_ROOT / "models" / "vision_svm_classifier_candidate.joblib",
        help="Candidate artifact. It never becomes active automatically.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=PROJECT_ROOT / "reports" / "recognition_training_candidate",
    )
    parser.add_argument("--min-quality-score", type=int, default=55)
    parser.add_argument("--min-per-class", type=int, default=20)
    parser.add_argument("--threshold", type=float, default=0.25)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Rebuild processed and train/validation/test directories after preserving manifests.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    try:
        _guard_candidate_output(config, args.output_model)
    except ValueError as exc:
        print(f"Treino interrompido: {exc}")
        return 2
    if not 0.0 < args.threshold <= 1.0:
        print("Treino interrompido: --threshold deve estar entre 0 e 1.")
        return 2
    source = (args.source or config.directories["curated_data"]).resolve()
    if not source.exists():
        print(f"Fonte não encontrada: {source}")
        return 2

    try:
        _guard_rebuild(config, args.overwrite)
    except RuntimeError as exc:
        print(f"Treino interrompido: {exc}")
        return 2

    source_counts = _image_count(source, config.classes, config.allowed_extensions)
    missing = {class_id: count for class_id, count in source_counts.items() if count < args.min_per_class}
    if missing:
        print("Treino interrompido: cada classe precisa de imagens curadas suficientes.")
        for class_id, count in missing.items():
            print(f"  {class_id}: {count}/{args.min_per_class}")
        return 2

    preparation_report = args.report_dir / "dataset_preparation"
    summary, _ = prepare_dataset_images(
        config,
        source_dir=source,
        output_dir=config.directories["processed_data"],
        report_dir=preparation_report,
        overwrite=args.overwrite,
        min_quality_score=args.min_quality_score,
    )
    if summary.prepared == 0:
        print("Treino interrompido: nenhuma imagem passou pela preparação técnica.")
        return 2

    split_records = split_dataset(
        config,
        source_dir=config.directories["processed_data"],
        overwrite=args.overwrite,
    )
    train_counts = Counter(record.class_id for record in split_records if record.split == "train")
    missing_train = [class_id for class_id in config.classes if train_counts[class_id] == 0]
    if missing_train:
        print(f"Treino interrompido: classes sem amostras de treino: {missing_train}")
        return 2

    args.report_dir.mkdir(parents=True, exist_ok=True)
    train_exit = train_visual_svm([
        "--output-model", str(args.output_model),
        "--report-dir", str(args.report_dir),
        "--threshold", str(args.threshold),
    ])
    if train_exit != 0:
        return int(train_exit)
    selection = json.loads((args.report_dir / "visual_svm_summary.json").read_text(encoding="utf-8"))
    contract = processing_contract(config)
    write_model_contract(args.output_model, contract)

    run = {
        "source": str(source),
        "classes": list(config.classes),
        "model_family": "visual_supervised",
        "selected_algorithm": selection["selected_candidate"],
        "processing_options": asdict(default_processing_options(config)),
        "processing_contract": contract,
        "config_sha256": hashlib.sha256(config.config_path.read_bytes()).hexdigest(),
        "source_counts": source_counts,
        "preparation": {
            "prepared": summary.prepared,
            "rejected": summary.rejected,
            "errors": summary.errors,
            "min_quality_score": args.min_quality_score,
        },
        "split_counts": {
            "train": dict(Counter(record.class_id for record in split_records if record.split == "train")),
            "validation": dict(Counter(record.class_id for record in split_records if record.split == "validation")),
            "test": dict(Counter(record.class_id for record in split_records if record.split == "test")),
        },
        "candidate_model": str(args.output_model),
        "candidate_sha256": hashlib.sha256(args.output_model.read_bytes()).hexdigest(),
        "active_model_changed": False,
        "next_step": "Revisar métricas e casos de confusão; promover somente após aceite independente.",
    }
    (args.report_dir / "training_run.json").write_text(
        json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Candidato de reconhecimento criado com sucesso.")
    print(f"Modelo candidato: {args.output_model}")
    print(f"Relatórios: {args.report_dir}")
    print("O modelo ativo não foi alterado automaticamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
