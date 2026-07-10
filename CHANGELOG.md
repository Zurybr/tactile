# Changelog

All notable changes to **tactile** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Fluency track** (`curriculum.py`): a post-speedtest curriculum track of
  70 new units (37 for en_us, 33 for es_la) and 254 new exercises covering
  bigrams/trigrams, common-word frequency tiers, sentence packs, paragraph
  packs, number drills, symbol drills, code snippets, and speed bursts. The
  key-introduction spine is preserved; the fluency track appends after the
  speedtest with its own 40→65 WPM ramp (the spine keeps 10→40), so the
  overall ramp stays monotonic. Added a `Unit.track` field
  (`"spine" | "fluency"`), the fluency `kind` set
  (`ngram`, `common_words`, `sentence`, `paragraph`, `number`, `symbol`,
  `code`, `burst`), and a newline/indent-preserving `_finalize` path used by
  paragraph and code units. All fluency content is original or
  traditional/public-domain (no copyrighted text); code is en_us-only
  because the es_la layout cannot type a backslash. Every generator is
  deterministic via a dedicated `"{layout}:fluency"` RNG namespace.
  Documented in `docs/engineering/curriculum.md`.

- **Color-coded practice text** (`practice.py`): typed characters now render
  green (correct) or red (uncorrected error) per-position, instead of a
  uniform green. Extracted `_build_text()` for testability.
- **Project icon** (`docs/assets/tactile-icon.svg`): terminal-themed SVG icon
  displayed in the README header.
- **Self-update subcommand** (`__main__.py`): `tactile update` reinstalls
  tactile from the latest `main` branch on GitHub
  (`git+https://github.com/Zurybr/tactile`). It prefers
  `uv tool install --force` and falls back to
  `pip install --upgrade --force-reinstall` when `uv` is not on PATH; any
  installer failure prints to stderr and exits 1. Documented in
  `docs/reference/cli.md`.
- **Cross-platform install scripts** (`install.ps1`, `install.sh`): one-line
  installers for Windows (PowerShell) and Linux/Mac (bash). Each installs
  `uv` first if it is missing, then runs
  `uv tool install git+https://github.com/Zurybr/tactile`. Documented in
  `README.md`.
- **GitHub Actions CI** (`.github/workflows/ci.yml`): runs the test suite
  (`uv run python -m pytest -q`), docs validation
  (`scripts/validate_docs.py`), and a build check (`uv build`) on
  `ubuntu-latest`, `windows-latest`, and `macos-latest` for Python 3.12 on
  every push and pull request to `main`.

- **Forgiving error model** (`engine.py`): a wrong key now ADVANCES the
  cursor (the learner types past mistakes), backspace ERASES the recorded
  error so the position can be re-evaluated, and a corrected position earns
  0.5 partial credit (first-try = 1.0, never-corrected = 0.0). Live
  accuracy reflects only attempted-so-far characters; final accuracy uses
  the full target length. Net WPM uses credited chars. Star thresholds
  (90/95/97/99) are unchanged; only the accuracy + net_wpm that feed them
  changed. The full cascade (error -> `_ever_errored` -> accuracy ->
  net_wpm -> stars -> record) is internally consistent. Documented in
  `docs/engineering/engine.md`.
- **Free lesson navigation** (`progress.py`, `screens/lesson_map.py`): any
  lesson, review, or speedtest is attemptable in any order — `is_unlocked`
  is always `True` and no lesson-map row is disabled. Completing a lesson
  with `>= 2` stars lights up the completion badges of every earlier lesson
  across all units globally (the completion cascade), shown via a separate
  `is_completion_unlocked` lock icon.
- **S/M/L text-size presets** (`screens/practice.py`, `styles.tcss`): cycle
  the practice-screen preset via `+`/`-` (wraps S -> M -> L -> S). Each
  preset swaps a CSS class that adjusts container width + text weight
  (L = 96% bold, M = 90% normal default, S = 80% dim) — terminals cannot
  scale glyph pixels, so use the terminal emulator's zoom for true zoom.
  The choice persists in `settings.size` and falls back to M on an invalid
  stored value. Documented in `docs/reference/keybinds.md`.
- **Centered practice-screen layout** (`styles.tcss`): title, stats, practice
  text, and keyboard now resolve to `text-align: center` for visual
  consistency. The results body stays centred as before. Ergonomics note
  (multi-line cursor anchor shift) and a possible future left-align escape
  hatch are documented in `docs/engineering/tui-screens.md`.

### Changed

- **Installation method** (`README.md`): end users now install tactile via
  one-line scripts (`install.ps1` / `install.sh`) or
  `uv tool install git+https://github.com/Zurybr/tactile` from GitHub,
  instead of cloning and running `uv sync`. The previous `uv sync` workflow is
  retained as "Development setup" for contributors.
- **Accuracy + net WPM formulas** (`engine.py`): accuracy now weights
  positions (first-try 1.0, corrected 0.5, uncorrected 0.0) instead of
  counting keystrokes; net WPM uses credited chars instead of `position`.
  Required because wrong keys now advance the cursor (so `position` no
  longer equals the correct count). Gross WPM is unchanged.
- **Progress schema v1 -> v2** (`progress.py`): adds a top-level `settings`
  object (default `{}`). Legacy v1 files migrate forward losslessly on load
  (version bumped to 2, `settings` added if absent, all stars / bests /
  `key_errors` preserved verbatim); the v1 file is copied to
  `progress.json.bak` before the first v2 write and is never treated as
  corrupt. The migration is forward-only and idempotent.

- **Contributor conventions** (`AGENTS.md`): mandatory documentation-sync,
  changelog-sync, conventional-commit-with-scope, and pre-push docs-validation
  rules for every change.
- **Docs validation script** (`scripts/validate_docs.py`): parses Obsidian
  wikilinks from `docs/index.md` and verifies every link resolves to a file
  under `docs/`. Run with `uv run python scripts/validate_docs.py` before
  pushing.

### Removed

- **Edclub hold-cursor error model** (`engine.py`): the previous behaviour
  (cursor held on wrong key; every wrong attempt counted against accuracy)
  is replaced wholesale by the forgiving model above. There is no opt-in
  toggle and no legacy code path — the forgiving model is the only model.

### Fixed

- **`tactile update` on Windows** (`__main__.py`): the update command no longer
  fails with "Access is denied" (os error 5) when the running executable locks
  the tool directory. On Windows, `_run_update` now creates a detached batch
  updater that waits for tactile to exit, runs `uv tool install --force`, and
  auto-deletes. The Unix path is unchanged.

## [0.1.0] - 2026-07-09

The first tagged release: a terminal touch-typing trainer built with Textual.

### Added

- **Core typing engine** (`engine.py`): pure domain logic implementing the
  edclub-style cursor model (cursor does not advance on a wrong key; every
  wrong attempt counts against accuracy), live WPM/accuracy, and a 1-5 star
  rating per exercise (1 complete; 2 acc>=90; 3 acc>=95; 4 acc>=97 and
  net WPM>=target; 5 acc>=99 and net WPM>=target).
- **Two keyboard layouts** (`layouts/`): English (US) QWERTY and
  Español (Latinoamérica). The es_la layout is verified against the Windows
  KBDLA layout, including the `ñ` home-row key, the `´`/`¨` dead keys
  producing accented vowels, and AltGr symbols (`AltGr+Q` = `@`).
- **Deterministic, layout-aware curriculum** (`curriculum.py`): one lesson per
  key-introduction group (home row outward), a review unit every 5th lesson,
  and a final speed test. Content is seeded by
  `(layout, unit_index, exercise_index)` so a given layout always produces the
  same curriculum. en_us yields 26 units (21 lessons + 4 reviews + 1 speed
  test); es_la yields 27 units (22 lessons + 4 reviews + 1 speed test).
- **Bundled wordlists**: 300 common words per language (`en.txt`, `es.txt`),
  loaded via `importlib.resources`. No network access at build or runtime.
- **Sequential unlocking**: a unit unlocks when the previous one has >=2
  stars. Replays are always allowed and can improve stars.
- **Progress store** (`progress.py`): schema-versioned JSON at
  `~/.tactile/progress.json` with atomic writes (write `.tmp`, then
  `os.replace`) and a `.bak` backup on corruption. Keeps best stars/WPM/
  accuracy per unit and accumulates a per-key error heatmap.
- **Textual TUI** (`app.py`, `screens/`, `widgets.py`): layout select, lesson
  map (with lock/star/best-WPM rows), practice (live stats, on-screen
  keyboard with finger + modifier hints), results (stars, worst keys, retry),
  and a directory-tree file picker.
- **Code/text file practice** (`codeload.py`): turn any file into typing
  exercises. utf-8 first with a latin-1 fallback; tabs expanded to 4 spaces;
  leading/trailing whitespace stripped; files capped at 2000 lines; untypable
  characters removed with a notice. Chunked into 10-line exercises. Results
  are shown but only the key-error heatmap is recorded (never lesson stars).
- **CLI** (`__main__.py`): `tactile` launches the trainer,
  `tactile practice <path>` jumps straight into code practice,
  `tactile --version` prints the version, and `python -m tactile` works too.
- **Test suite**: 76 tests (pytest + pytest-asyncio) covering the engine,
  layouts, curriculum, progress store, code loader, and Textual Pilot-driven
  UI flows. Strict TDD was used throughout.

[0.1.0]: https://keepachangelog.com/en/1.1.0/
