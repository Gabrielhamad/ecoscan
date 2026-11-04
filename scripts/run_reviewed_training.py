"""Process one reviewed contribution queue scan in the private worker."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ecoscan.config import load_config
from ecoscan.services.contribution_store import remote_store
from ecoscan.training.semantic_learning import run


def main() -> None:
    store = remote_store()
    if store is None:
        raise SystemExit("Private database connection is required.")
    print("Training queue:", run(load_config(), store))


if __name__ == "__main__":
    main()
