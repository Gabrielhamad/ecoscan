"""Execute one queue scan; use a single scheduled worker for this project."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ecoscan.config import load_config
from ecoscan.services.contribution_store import remote_store
from ecoscan.training.automatic import run

if __name__ == "__main__":
    store = remote_store()
    if store is None:
        raise SystemExit("Private database connection is required.")
    config = load_config()
    if config.model.get("semantic_preview_enabled", False):
        from ecoscan.training.semantic_learning import run
    print("Training queue:", run(config, store))
