"""Import the secretariat export without changing the deployed model."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ecoscan.config import load_config
from ecoscan.training.contribution_import import import_approved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    result = import_approved(args.package, args.destination, load_config().classes)
    print(f"Importadas: {len(result['images'])}. Treino e publicacao ainda pendentes.")


if __name__ == "__main__":
    main()
