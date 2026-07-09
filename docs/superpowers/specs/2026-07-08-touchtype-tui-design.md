# touchtype — TUI Touch-Typing Trainer (Design Spec)

Date: 2026-07-08
Status: Approved by user (design conversation, this session)
Stack: Python 3.14 + Textual, managed with uv

## Purpose

A terminal (TUI) touch-typing trainer modeled on edclub/TypingClub:
progressive lessons that introduce keys outward from the home row, live
WPM/accuracy feedback, a star-based progression with sequential unlocking,
an on-screen keyboard with next-key and finger hints — plus a practice mode
that loads any code/text file and turns it into typing exercises.

Single local user. Runs on Windows Terminal (primary), any modern terminal.

## Decisions (locked)

- **Language/stack**: Python + Textual (chosen over prompt_toolkit and curses).
- **Layouts**: BOTH `en_us` (QWERTY US) and `es_la` (Latin American Spanish),
  selectable at startup and switchable later. Curriculum is generated per
  layout from layout data; the typing engine is layout-agnostic.
- **Cursor model (edclub behavior)**: the cursor does NOT advance on a wrong
  key. Every wrong attempt counts against accuracy. Backspace steps back one
  position (rarely needed under this model).
- **Stars (1–5)**: 1★ complete · 2★ ≥90% accuracy · 3★ ≥95% · 4★ ≥97% and
  lesson WPM target · 5★ ≥99% and lesson WPM target. WPM targets ramp from
  10 (early lessons) to 40 (late lessons).
- **Unlocking**: a lesson unlocks when the previous one has ≥2★. Replays are
  always allowed and can improve stars.
- **UI copy**: English.
- **Package name**: `touchtype` (src layout). The folder name "touchtiping"
  is a typo and is not inherited by the code.

## Architecture (4 layers, dependencies point downward only)

```
UI (Textual app + screens)      app.py, screens/, styles.tcss
  -> Progression                progress.py   (JSON persistence, stars, unlocks)
  -> Content                    curriculum.py, layouts/, wordlists/
  -> Engine                     engine.py     (pure domain, no I/O, no Textual)
```

### 1. Engine (`engine.py`) — pure, strict-TDD target

`TypingSession(target: str)` processes key events and exposes state:

- `on_key(char)` — advance if `char == expected`, else record an error at the
  current index (cursor stays). `on_backspace()` — step back one if possible.
- Metrics: elapsed time (starts at first keystroke), gross/net WPM
  (net WPM = correct chars / 5 / minutes), accuracy = correct keystrokes /
  total keystrokes, per-target-index error counts, per-expected-char error
  counts (feeds the key heatmap).
- `is_complete`, `stars(wpm_target)` per the thresholds above.
- Newlines in targets: expected char `\n` is satisfied by Enter.
- The engine never touches the clock directly in tests: time source injectable.

### 2. Content (`layouts/`, `curriculum.py`, `wordlists/`)

Layout = data (Python dicts, no parser):

- `rows`: physical key caps per row (for on-screen keyboard rendering).
- `char_map`: char -> (row, col, finger, modifier) where modifier is
  none/shift/altgr. `es_la` home row is `a s d f j k l ñ`; accented vowels
  (á é í ó ú) map to dead-key ´ + vowel — hint shows the vowel key; ü, ¿, ¡
  included in late lessons. `en_us` includes the full ASCII code-symbol set.
- `key_order`: ordered introduction groups, home row outward, e.g. en_us:
  `f j`, `d k`, `s l`, `a ;`, `g h`, `e i`, `r u`, `t y`, `w o`, `q p`,
  `v m`, `b n`, `c ,`, `x .`, `z /`, shift/capitals, numbers, common
  punctuation, code symbols (`{ } [ ] ( ) < > _ = + - * & | ! " ' ` ~ # % ^`).
  es_la analogous with ñ, accents, and its own punctuation placement.

Curriculum is generated deterministically from the layout:

- ~20–24 units per layout; each unit has 3–5 exercises progressing
  drill -> words -> sentences. Drills are patterned key sequences
  (`fff jjj fjf jfj`); word exercises sample the bundled wordlist filtered to
  the learned key pool; sentence exercises appear once the pool allows.
- Wordlists bundled as plain text: English for en_us, Spanish (with ñ and
  accents) for es_la; a few hundred common words each, no network access.
- Every 5th unit is a review (mixed content from all learned keys); a speed
  test closes each major block (home row, top row, bottom row, symbols).
- Determinism: exercises are generated with a seeded RNG keyed by
  (layout, unit index, exercise index) so content is stable across runs.

### 3. Progression (`progress.py`)

JSON at `~/.touchtype/progress.json` (schema versioned):

```json
{
  "version": 1,
  "active_layout": "en_us",
  "layouts": {
    "en_us": {
      "lessons": {"<unit-id>": {"stars": 3, "best_wpm": 32.5, "best_acc": 96.4}},
      "key_errors": {"f": 12, ";": 40}
    }
  }
}
```

Corrupt/missing file -> start fresh (never crash on load). Atomic writes
(write temp, replace).

### 4. UI (Textual)

Screens:

- **Layout select** (first run and on demand).
- **Lesson map**: scrollable list of units with lock/star state; enter to play.
- **Practice**: target text with cursor; typed chars colored (green correct,
  red mark on error position); live WPM/accuracy; on-screen keyboard
  highlighting the next key (and shift/altgr hint) plus finger name.
- **Results**: stars earned, WPM, accuracy, worst keys; retry / continue.
- **Code practice**: reached via CLI `touchtype practice <file>` or a
  DirectoryTree picker in-app.

Code practice specifics:

- File is split into exercises of ~10 lines each.
- Leading whitespace is auto-skipped per line (cursor starts at the first
  non-blank char; Enter completes a line) — editors handle indentation in
  real life. Tabs are expanded to 4 spaces for display/typing.
- Chars not typable in the active layout are shown dimmed and auto-skipped
  with a visible notice. Encoding: utf-8 with latin-1 fallback. Files longer
  than 2000 lines: first 2000 with a notice.

## CLI

- `touchtype` — launch app (lesson map).
- `touchtype practice <path>` — jump straight into code practice for a file.
- Entry points: `python -m touchtype` and a `touchtype` console script.

## Error handling summary

Unreadable file -> friendly in-app error; corrupt progress -> fresh start
with backup of the bad file; terminal too small -> Textual's standard
handling; unknown chars -> skip + notice.

## Testing

- **Strict TDD** for engine, curriculum generation, and progress persistence
  (pure logic, no UI). pytest, run via `uv run pytest`.
- One headless UI smoke test with Textual Pilot: launch -> select layout ->
  open lesson 1 -> type the full first exercise -> results screen shows stars.
- Definition of done: full test suite green, `uv run touchtype --help` (or
  `python -m touchtype --help`) works, app launches.

## Out of scope (v1)

Multiple user profiles, cloud sync, custom lesson authoring UI, sound,
detailed per-finger analytics dashboards, non-QWERTY layouts (Dvorak etc.),
localization of UI copy.
