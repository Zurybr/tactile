# tactile

A terminal touch-typing trainer built with [Textual](https://textual.textualize.io/).

![Python](https://img.shields.io/badge/python-%E2%89%A5%203.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-76%20passed-brightgreen)

tactile teaches touch typing with progressive lessons that introduce keys
outward from the home row (edclub/TypingClub style). It shows live WPM and
accuracy, rates each unit 1-5 stars, unlocks the next unit at >=2 stars, and
renders an on-screen keyboard with finger and modifier hints. It also turns
any code or text file into typing practice.

## Features

- **Progressive, layout-aware curriculum** — keys are introduced home-row
  outward, with a review every 5th unit and a final speed test.
- **Live feedback** — WPM and accuracy update while you type; the on-screen
  keyboard highlights the next key and shows the finger + modifier
  (`Shift`, `AltGr`, dead key) to use.
- **1-5 star rating** — 1 for completing, up to 5 for >=99% accuracy at the
  unit's WPM target. A unit unlocks the next at >=2 stars.
- **Two keyboard layouts** — English (US) and Español (Latinoamérica), each
  with its own generated curriculum and its own progress.
- **Code/text file practice** — point tactile at any file and type it, in
  10-line chunks. utf-8 with a latin-1 fallback, tabs expanded, untypable
  characters skipped with a notice.
- **Resilient progress** — schema-versioned JSON, written atomically; a
  corrupt file is backed up to `progress.json.bak` and the app starts fresh.
- **Offline** — bundled wordlists, no network at build or runtime.

## Screenshots

Screenshots will be added here. *(No images are bundled yet.)*

## Requirements

- **Python >= 3.12**
- **[uv](https://docs.astral.sh/uv/)** (package manager and build backend)

## Installation

```sh
uv sync
```

This creates a `.venv`, installs `tactile` and its single runtime dependency
(`textual>=0.60`), and the `dev` dependency group (`pytest`, `pytest-asyncio`).

## Usage

Launch the trainer:

```sh
uv run tactile
```

Practice typing a code or text file:

```sh
uv run tactile practice path/to/file.py
```

`python -m tactile` works as well. The first run asks you to pick a layout;
later runs remember it.

### In-app keybindings

| Key      | Screen            | Action                          |
|----------|-------------------|---------------------------------|
| `enter`  | Layout select     | Pick the highlighted layout     |
| `enter`  | Lesson map        | Open the highlighted unit       |
| `enter`  | Results           | Return to the lesson map        |
| `escape` | Practice          | Back to the lesson map          |
| `escape` | File picker       | Cancel, back to the lesson map  |
| `r`      | Results           | Retry the unit                  |
| `p`      | Lesson map        | Open the file picker            |
| `l`      | Lesson map        | Change keyboard layout          |
| `q`      | Lesson map        | Quit tactile                    |

See [`docs/reference/keybinds.md`](docs/reference/keybinds.md) and
[`docs/reference/cli.md`](docs/reference/cli.md) for the full reference.

## Layouts

Two layouts ship with tactile, selectable at startup and switchable later
with the `l` key:

- **English (US)** — QWERTY US, full ASCII symbol set.
- **Español (Latinoamérica)** — home row with `ñ`, the `´`/`¨` dead keys
  producing accented vowels, and AltGr symbols (`AltGr+Q` = `@`). Physical
  positions are verified against the Windows KBDLA layout.

Each layout gets its own generated curriculum and its own progress, stored
per-layout in `~/.tactile/progress.json`.

## Project structure

```
src/tactile/
├── __init__.py          # package version
├── __main__.py          # CLI entry point (argparse: practice <path>, --version)
├── app.py               # TactileApp shell: wires progression, content, screens
├── engine.py            # TypingSession: pure typing logic, cursor model, stars
├── curriculum.py        # build_curriculum: deterministic, layout-aware units
├── progress.py          # ProgressStore: JSON schema, atomic writes, unlocks
├── codeload.py          # load_code_exercises: turn a file into typing chunks
├── widgets.py           # KeyboardWidget + render_stars
├── styles.tcss          # Textual CSS
├── layouts/
│   ├── __init__.py      # KeyInfo, Layout, build_char_map, add_dead_key_vowels
│   ├── en_us.py         # English (US) QWERTY data
│   └── es_la.py         # Español (Latinoamérica) data (KBDLA-verified)
├── screens/
│   ├── layout_select.py # pick a layout (first run, or via `l`)
│   ├── lesson_map.py    # scrollable unit list with lock/star/best-WPM
│   ├── practice.py      # the typing loop, live stats, keyboard hints
│   ├── results.py       # stars, WPM, accuracy, worst keys, retry/continue
│   └── file_picker.py   # DirectoryTree over cwd for code practice
└── wordlists/
    ├── en.txt           # 300 common English words
    └── es.txt           # 300 common Spanish words (with ñ and accents)
```

## Documentation

The full documentation lives under [`docs/`](docs/index.md) — start at
[`docs/index.md`](docs/index.md) for a navigable map of the project,
engineering notes, decisions, and reference pages.

## Contributing

Contributions are welcome. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) for the
setup, the strict-TDD expectation, the commit style, and the PR flow. By
participating you agree to uphold the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md).

## License

MIT License — see [`LICENSE`](LICENSE). Copyright (c) 2026 Brandom Ledesma.
