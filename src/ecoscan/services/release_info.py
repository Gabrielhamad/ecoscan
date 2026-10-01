"""Non-sensitive build identity for support and recognition feedback."""
from functools import lru_cache
from pathlib import Path
import re
import subprocess

from ecoscan import __version__


@lru_cache(maxsize=1)
def code_revision() -> str | None:
    root = Path(__file__).resolve().parents[3]
    try:
        # Avoid reporting a parent workspace's commit when this is a source copy.
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=root,
            capture_output=True, text=True, timeout=2, check=True,
        ).stdout.strip()
        if Path(top).resolve() != root:
            return None
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root,
            capture_output=True, text=True, timeout=2, check=True,
        ).stdout.strip()
        return revision if re.fullmatch(r"[0-9a-f]{40,64}", revision) else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def release_info() -> dict:
    return {"app_version": __version__, "code_revision": code_revision()}
