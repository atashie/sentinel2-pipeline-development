"""Every relative Markdown link in the repository must resolve to a file or directory."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)")
SKIP_DIRS = {".venv", ".uv-cache", ".git", "data", "dist", ".pytest_cache", ".ruff_cache"}


def markdown_files():
    for path in ROOT.rglob("*.md"):
        if not SKIP_DIRS & set(path.relative_to(ROOT).parts):
            yield path


@pytest.mark.parametrize("path", sorted(markdown_files()), ids=lambda p: str(p.relative_to(ROOT)))
def test_relative_links_resolve(path):
    broken = []
    for target in LINK.findall(path.read_text()):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        if not (path.parent / target).exists():
            broken.append(target)
    assert not broken, f"{path.relative_to(ROOT)}: {broken}"
