"""Prepare a private corpus locally; does not upload images or publish models."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ecoscan.config import load_config
from ecoscan.training.corpus import build_corpus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_corpus(json.loads(args.manifest.read_text(encoding="utf-8")),
                          args.source, args.output, load_config().classes)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
