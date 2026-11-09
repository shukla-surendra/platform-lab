"""Rebuild docs/ as a symlink farm pointing at the real Markdown source files.

No content is copied — every file under docs/ is a symlink back to the
single canonical .md file elsewhere in the repo, so editing vocab.md (or
anything else) is immediately reflected the next time `mkdocs serve`
live-reloads. Safe to re-run any time: it only ever removes symlinks it
created, never a real file.

Usage: python3 scripts/link_mkdocs_docs.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
EXCLUDE_DIRS = {".venv", ".git", "docs_html", "docs", "site", "__pycache__", "source", "experiments", "mkdocs-site"}
# Site-only files (landing page, flashcards page, CSS/JS) live here and are linked into the
# docs/ root rather than under their own folder name.
SITE_EXTRAS = ROOT / "mkdocs-site"
SITE_EXTRA_DIRS = ("pages", "assets")


def find_markdown_files():
    for path in sorted(ROOT.rglob("*.md")):
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if rel == Path("CLAUDE.md"):
            continue
        yield path


def main():
    # Clear out any previous symlink farm (never touches real files, since
    # DOCS only ever contains symlinks this script created).
    if DOCS.exists():
        for path in sorted(DOCS.rglob("*"), reverse=True):
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    DOCS.mkdir(exist_ok=True)

    count = 0
    for src in find_markdown_files():
        rel = src.relative_to(ROOT)
        dest = DOCS / rel
        if src.name == "README.md" and rel.parent == Path("."):
            # mkdocs-site/pages/index.md is the landing page; the repo README becomes an "About" page.
            dest = DOCS / "overview.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        target = Path("../" * (len(dest.relative_to(DOCS).parts))) / rel
        dest.symlink_to(target)
        count += 1

    # mkdocs-site/pages/** and mkdocs-site/assets/** -> docs/** (pages/ prefix dropped)
    for sub in SITE_EXTRA_DIRS:
        base = SITE_EXTRAS / sub
        if not base.exists():
            continue
        for src in sorted(base.rglob("*")):
            if src.is_dir() or "__pycache__" in src.parts:
                continue
            rel_in = src.relative_to(base) if sub == "pages" else Path(sub) / src.relative_to(base)
            dest = DOCS / rel_in
            dest.parent.mkdir(parents=True, exist_ok=True)
            target = Path("../" * (len(rel_in.parts) - 1)) / ".." / src.relative_to(ROOT)
            dest.symlink_to(target)
            count += 1

    print(f"Linked {count} Markdown files into {DOCS.relative_to(ROOT)}/ (symlinks only, no copies).")


if __name__ == "__main__":
    main()
