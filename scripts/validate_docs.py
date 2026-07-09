#!/usr/bin/env python3
"""Validate that docs/index.md exists and its wikilinks resolve to real files.

Parses Obsidian wikilinks of the form ``[[path|alias]]`` and ``[[path]]``
(and ``[[path#section]]``) from ``docs/index.md`` and checks that each path
points to an existing file under ``docs/``. Exits non-zero if
``docs/index.md`` is missing or any link is broken.

Run it before pushing:

    uv run python scripts/validate_docs.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
INDEX = DOCS_DIR / "index.md"
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def strip_code(text: str) -> str:
    """Remove fenced code blocks and inline code.

    Wikilinks that appear inside code (syntax examples, demos) are not real
    links and must not be validated.
    """
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", "", text)
    return text


def parse_wikilinks(text: str) -> list[str]:
    """Return the path part of each ``[[path|alias]]`` / ``[[path]]`` link.

    Section anchors (``[[path#section]]``) and aliases (``[[path|alias]]``)
    are stripped: only the path is validated. Code spans are removed first so
    ``[[file]]``-style examples are not mistaken for real links.
    """
    text = strip_code(text)
    paths: list[str] = []
    for match in WIKILINK_RE.finditer(text):
        target = match.group(1)
        path = target.split("|", 1)[0].split("#", 1)[0].strip()
        if path:
            paths.append(path)
    return paths


def resolve(path: str) -> Path | None:
    """Return the file a wikilink path points to, or None if it does not exist.

    Wikilinks are relative to ``docs/`` and omit the ``.md`` extension, so
    both ``docs/<path>`` and ``docs/<path>.md`` are tried.
    """
    candidate = DOCS_DIR / path
    if candidate.is_file():
        return candidate
    if not path.endswith(".md"):
        with_ext = DOCS_DIR / f"{path}.md"
        if with_ext.is_file():
            return with_ext
    return None


def main() -> int:
    if not INDEX.is_file():
        print(f"FAIL: {INDEX.relative_to(REPO_ROOT)} does not exist.",
              file=sys.stderr)
        return 1

    text = INDEX.read_text(encoding="utf-8")
    links = parse_wikilinks(text)

    if not links:
        print(f"WARN: no wikilinks found in "
              f"{INDEX.relative_to(REPO_ROOT)}", file=sys.stderr)

    broken: list[str] = []
    for link in links:
        if resolve(link) is not None:
            print(f"ok   {link}")
        else:
            broken.append(link)
            print(f"FAIL {link}", file=sys.stderr)

    if broken:
        print(f"\n{len(broken)} broken wikilink(s) in "
              f"{INDEX.relative_to(REPO_ROOT)}:", file=sys.stderr)
        for b in broken:
            print(f"  - [[{b}]]", file=sys.stderr)
        return 1

    print(f"\nOK: {len(links)} wikilink(s) resolved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
