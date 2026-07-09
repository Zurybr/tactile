"""Load a code/text file and turn it into typing exercises.

Pure logic module - no Textual dependency. Processing rules:

- utf-8 first, latin-1 fallback (with a notice).
- Tabs expand to 4 spaces; trailing whitespace is stripped; leading
  whitespace is dropped (editors handle indentation in real life).
- Blank lines are skipped; files are capped at 2000 lines (with a notice).
- Characters the active layout cannot type are removed (single notice
  listing the sorted unique characters that were skipped).
- Exercises are chunks of 10 processed lines joined with newlines.
"""

from __future__ import annotations

from pathlib import Path

from touchtype.curriculum import Exercise
from touchtype.layouts import Layout

_MAX_LINES = 2000
_LINES_PER_EXERCISE = 10
_TAB_SIZE = 4


def load_code_exercises(path: Path, layout: Layout) -> tuple[list[Exercise], list[str]]:
    notices: list[str] = []
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
        notices.append("decoded as latin-1")

    lines = text.splitlines()
    if len(lines) > _MAX_LINES:
        lines = lines[:_MAX_LINES]
        notices.append(f"truncated to first {_MAX_LINES} lines")

    skipped_chars: set[str] = set()
    processed: list[str] = []
    for line in lines:
        line = line.expandtabs(_TAB_SIZE).rstrip().lstrip()
        kept_chars: list[str] = []
        for char in line:
            if layout.typable(char):
                kept_chars.append(char)
            else:
                skipped_chars.add(char)
        line = "".join(kept_chars)
        if line:
            processed.append(line)

    if skipped_chars:
        notices.append(f"skipped untypable: {''.join(sorted(skipped_chars))}")

    exercises = [
        Exercise(text="\n".join(processed[start : start + _LINES_PER_EXERCISE]))
        for start in range(0, len(processed), _LINES_PER_EXERCISE)
    ]
    return exercises, notices
