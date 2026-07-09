# Development

How to set up, run, test, and extend tactile. This is the contributor's
working reference.

## Quick path

```sh
uv sync                  # create .venv, install tactile + dev deps
uv run tactile           # launch the trainer
uv run pytest -q         # 76 passed
```

Requires **Python >= 3.12** and **[uv](https://docs.astral.sh/uv/)**. See
[project/uv.md](../project/uv.md) for why uv.

## Environment setup

```sh
git clone <your-fork-url>
cd tactile
uv sync
```

`uv sync` creates `.venv`, installs the single runtime dependency
(`textual>=0.60`) and the `dev` group (`pytest`, `pytest-asyncio`), and
installs the `tactile` package in editable form. A committed `uv.lock`
makes the install reproducible.

## Running the app

```sh
uv run tactile                              # lesson map (or layout select on first run)
uv run tactile practice path/to/file.py     # jump straight into code practice
uv run python -m tactile                    # same as `tactile`
uv run python -m tactile --version          # prints "tactile 0.1.0"
```

Progress is read from and written to `~/.tactile/progress.json`. To reset
all progress, delete that file (a corrupt file is backed up to
`progress.json.bak` automatically).

## Running the tests

```sh
uv run pytest -q                # whole suite, quiet
uv run pytest -q -x             # stop on first failure
uv run pytest tests/test_engine.py -q        # one module
uv run pytest tests/test_practice_flow.py -q # the Pilot tests
```

See [testing.md](testing.md) for what each test file covers and how to write
a new Pilot test.

## Project layout

```
tactile/
├── pyproject.toml          # project + uv_build + pytest config + dev group
├── uv.lock                 # pinned dependencies
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── LICENSE
├── src/tactile/            # the package (see docs/engineering/overview.md)
├── tests/                  # 7 test files, 76 cases
└── docs/                   # this documentation
```

The package uses a `src/` layout, so `tactile` is only importable after
`uv sync` installs it. This prevents accidentally testing the source tree
without installing it.

## The code-practice mode

Two ways in:

- **CLI** — `tactile practice path/to/file.py` opens the file directly in
  code practice, over the active layout (or `en_us` if none is set yet).
- **In-app** — from the lesson map, press `p` to open a `DirectoryTree`
  over the current working directory and pick a file.

Processing rules (in `codeload.py`):

- utf-8 first; on `UnicodeDecodeError`, retry latin-1 and add a notice.
- Tabs expand to 4 spaces; trailing whitespace is stripped; leading
  whitespace is dropped (editors handle indentation in real life).
- Blank lines are skipped; files are capped at 2000 lines (with a notice).
- Characters the active layout cannot type are removed, and a single notice
  lists the sorted unique skipped characters.
- Exercises are chunks of 10 processed lines joined with `\n`.

Code-practice results are shown but **not** recorded as lesson progress —
only the key-error heatmap accumulates.

## Adding a new layout or wordlist

1. **Add the layout data.** Create `src/tactile/layouts/<id>.py` with
   `_ROWS`, `_FINGERS`, `_SHIFT_PAIRS`, and (optionally) `_ALTGR_PAIRS`,
   plus a `KEY_ORDER_<X>` list of `(unit_title, new_chars)` tuples. Build
   the `char_map` with `build_char_map`; if the layout has dead keys, call
   `add_dead_key_vowels` afterwards. Construct and export the `Layout`.
2. **Register it.** Add the layout to `LAYOUTS` in
   `src/tactile/layouts/__init__.py`.
3. **Add a wordlist.** Drop a `<id>.txt` (one lowercase word per line, a
   few hundred common words) into `src/tactile/wordlists/` and add an entry
   to `_WORDLIST_FILES` in `curriculum.py`.
4. **Test it.** In `tests/test_layouts.py`, assert the home row, the key
   modifiers, that every `key_order` char is `typable()`, and that no char
   repeats across `key_order` entries. Add a curriculum test that the new
   layout builds and its review units eventually use its special chars.

Keep the pure-logic rule: `layouts/` must not import Textual or do I/O.

## Adding a new screen

1. Create `src/tactile/screens/<name>.py` with a `Screen` subclass.
2. `compose()` the widgets; declare `BINDINGS` for any keys.
3. **Do not import other screens.** Trigger transitions by calling
   `self.app.<method>()`, and add that method to `TactileApp` if it does not
   exist yet.
4. Write a `Pilot` test (see [testing.md](testing.md#writing-a-pilot-test))
   before implementing the behaviour.

## Code style reminders

- English for all code, comments, identifiers, and UI copy.
- `from __future__ import annotations` at the top of every module.
- Pure-logic modules (`engine`, `curriculum`, `progress`, `codeload`,
  `layouts`) must not import Textual or do I/O.
- Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`);
  no "Co-Authored-By" or AI attribution.
- Update `CHANGELOG.md` under `[Unreleased]` for user-facing changes.
