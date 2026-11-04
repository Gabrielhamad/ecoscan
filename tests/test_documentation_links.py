from pathlib import Path
import re
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")
IGNORED_PARTS = {".git", ".venv", ".pytest_cache", ".ruff_cache"}


def markdown_files():
    return (
        path
        for path in ROOT.rglob("*.md")
        if not IGNORED_PARTS.intersection(path.relative_to(ROOT).parts)
    )


def test_local_markdown_links_resolve():
    broken = []
    for document in markdown_files():
        for raw_target in LINK.findall(document.read_text(encoding="utf-8")):
            target = raw_target.strip().strip("<>").split(maxsplit=1)[0]
            if target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            relative = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if relative and not (document.parent / relative).resolve().exists():
                broken.append(f"{document.relative_to(ROOT)} -> {target}")
    assert broken == [], "Links locais quebrados:\n" + "\n".join(broken)
