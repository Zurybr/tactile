# Exploration: UX Improvements (text size, alignment, error model, unlock model)

Read-only investigation of 4 UX aspects of `tactile` today. No code changed.
Source of truth: `src/tactile/` (engine.py, curriculum.py, progress.py, widgets.py,
styles.tcss, app.py, screens/). Tests: `tests/test_engine.py` (13),
`tests/test_progress.py` (9), `tests/test_practice_flow.py` (4) — all green.

---

## Current State

### 1. Text size control — NONE EXISTS

A grep for `font|text-size|zoom|scale|font_size|text_size` over `src/` returns **zero
matches**. There is no user-facing setting, no CLI flag, no keybinding, and no CSS
hook to change text size.

- `styles.tcss` uses only: `width`, `padding`, `border`, `color`, `text-style`
  (`bold`, `italic`, `dim`), `text-align`, `align`, `background`. No sizing tokens.
- `widgets.py::KeyboardWidget._render_keyboard` (line 55) and
  `screens/practice.py::_refresh_text` (line 150) build `rich.text.Text` objects with
  **style spans only** (`"bold reverse"`, `"dim"`, `"italic"`, `"green"`, `"reverse"`,
  `"reverse red"`). Rich styles carry no size.
- The whole UI is rendered in the terminal's character grid; the **terminal emulator**
  controls the actual font, not the TUI app.

**Hard constraint**: a terminal app cannot change the glyph font-size in pixels. The
only levers are (a) layout `width`/`padding` (more whitespace = visually larger
block), (b) `text-style: bold` (heavier weight), and (c) reducing concurrent text so
each line is more prominent. True "zoom" is a terminal-emulator feature (Ctrl+),
outside the app's reach.

### 2. Text alignment / centering — partial, inconsistent

Only **two** alignment declarations exist in the entire codebase (grep
`text-align|align:` over `src/` → 2 hits):

- `styles.tcss:3` — `Screen { align: center middle; }` centers the **widget
  containers** vertically+horizontally inside the screen.
- `styles.tcss:37` — `#results-body { text-align: center; }` centers the **results
  text** inside its box.

Everything else has **no `text-align`**, so it defaults to left-aligned within its
`width: 90%` container:

| Widget | id | width | text-align | Effective look |
|--------|----|-------|-----------|----------------|
| practice title | `#practice-title` | 90% | none | left |
| practice stats | `#practice-stats` | 90% | none | left |
| practice text | `#practice-text` | 90% | none | left (target string left-justified) |
| keyboard | `#practice-keyboard` | 90% | none | left + per-row stagger indent (`" " * row_index`, widgets.py:59) |
| results body | `#results-body` | 60% | **center** | centered |
| OptionList | — | 90% | n/a (OptionList) | left per option |

So the **containers** are centered on screen, but the **text inside** the practice
title/stats/text/keyboard is left-aligned, while only the results body is centered.
This produces a visually inconsistent practice screen (left-justified text block in a
centered 90% column) vs. the centered results screen.

### 3. Error handling & scoring in engine — edclub "hold cursor" model

`engine.py::TypingSession.on_key` (line 81):

```python
self._total_keystrokes += 1
if char == expected:
    self._correct_keystrokes += 1
    self._position += 1
    return True
self._error_positions[self._position] = ... + 1   # where
self._key_errors[expected] = ... + 1              # which expected char
return False   # cursor stays
```

- **Wrong key does NOT block input** — `on_key` returns `False` and `position` is
  unchanged, but the learner can immediately press again. They are forced to type the
  correct key to advance (the "edclub cursor model", documented in
  `docs/engineering/engine.md`).
- **Every wrong attempt counts against accuracy**: `accuracy = correct / total * 100`
  (line 64). Pinned by `test_accuracy_with_mixed_correct_and_wrong_attempts`
  (test_engine.py:49) and `test_wrong_key_does_not_advance_and_records_error`
  (test_engine.py:28).
- **Backspace** (`on_backspace`, line 95): decrements `position` if `> 0`, but does
  **not** erase recorded errors or keystrokes (`test_backspace_does_not_erase_recorded_errors`,
  test_engine.py:127).
- **Scoring**:
  - `net_wpm = (position / 5) / minutes` (line 55) — uses correctly-typed chars only.
  - `gross_wpm = (total_keystrokes / 5) / minutes` (line 51) — includes wrong attempts.
  - `stars(wpm_target)` (line 100): `0` while incomplete, else a monotone ladder on
    accuracy with a WPM gate at the top two rungs:
    `1` complete → `2` acc≥90 → `3` acc≥95 → `4` acc≥97 **and** net_wpm≥target →
    `5` acc≥99 **and** net_wpm≥target. Thresholds:
    `_STAR_ACCURACY_THRESHOLDS = (90.0, 95.0, 97.0, 99.0)` (line 13). Pinned by the
    parametrized `test_stars_ladder_boundaries_driven_by_accuracy` (test_engine.py:73).
- **Unit aggregation** (screens/practice.py:106-112): `stars = min` across exercises,
  `accuracy`/`wpm` = mean. Progress store keeps the **best** (max) across replays.

### 4. Lesson unlock model — strictly sequential, threshold = 2 stars

`progress.py::ProgressStore.is_unlocked` (line 110):

```python
if unit_index == 0:
    return True
previous_unit = units[unit_index - 1]
return self.stars_for(layout_id, previous_unit.id) >= 2
```

- Unit 0 always unlocked. Every later unit unlocks iff the **immediately previous**
  unit has `>= 2` stars. Pinned by `test_unlock_logic_first_unit_always_unlocked_second_needs_two_stars`
  (test_progress.py:46).
- `curriculum.build_curriculum` (curriculum.py:60) emits lessons in `layout.key_order`
  order, inserting a `review` every 5 lessons and a final `speedtest`. **Reviews and
  the speedtest are normal units in the same sequence** — they are gated by the same
  "previous unit ≥ 2 stars" rule (no special treatment).
- `LessonMapScreen.refresh_options` (lesson_map.py:41) reads `is_unlocked` per row,
  disables locked rows, and lands the cursor on the first unlocked unit.
- `results_continue` (app.py:117) calls `refresh_options()` so a fresh 2+ stars
  unlocks the next row immediately.

**Progress JSON** (`~/.tactile/progress.json`, schema v1, progress.py:22):

```json
{
  "version": 1,
  "active_layout": "en_us",
  "layouts": {
    "en_us": {
      "lessons": { "en_us-01": {"stars": 4, "best_wpm": 32.5, "best_acc": 97.2} },
      "key_errors": {"f": 12, ";": 40}
    }
  }
}
```

`record()` (progress.py:73) keeps bests with `max(existing, new)`; `key_errors`
**accumulate** (never lowered). There is **no** completion flag, no timestamp, no
per-exercise breakdown, no user settings/preferences section, and no skip/unlock-token
field. Schema mismatch (wrong `version`) triggers the corrupt-file path: rename to
`.bak`, start fresh (progress.py:42, `test_corrupt_file_is_backed_up_and_store_starts_fresh`).

---

## Affected Areas

- `src/tactile/styles.tcss` — the single styling source; alignment + any size proxy.
- `src/tactile/widgets.py` — `KeyboardWidget._render_keyboard` (stagger indent, styles); `render_stars`.
- `src/tactile/screens/practice.py` — `_refresh_text` (cursor rendering), `_refresh_all`, `on_key`, `_finish_exercise` (aggregation/scoring).
- `src/tactile/engine.py` — `TypingSession.on_key`, `on_backspace`, `accuracy`, `net_wpm`, `stars`, `_STAR_ACCURACY_THRESHOLDS`. Pure domain; most test-pinned area.
- `src/tactile/progress.py` — `is_unlocked`, `record`, `_default_state`, `_SCHEMA_VERSION`. Schema + unlock policy.
- `src/tactile/curriculum.py` — `build_curriculum` unit ordering (reviews/speedtest gating).
- `src/tactile/app.py` — navigation/wiring; settings plumbing if added.
- `src/tactile/screens/lesson_map.py` + `screens/results.py` — display of alignment + stars.
- `src/tactile/__main__.py` — CLI surface if new flags/commands added.
- Docs (per AGENTS.md mapping): `docs/engineering/engine.md`, `tui-screens.md`, `progress.md`, `reference/cli.md`, `reference/progress-schema.md`; `CHANGELOG.md`.
- Tests: `tests/test_engine.py`, `test_progress.py`, `test_practice_flow.py`, `test_app.py`.

---

## Approaches (per aspect)

### Aspect 1 — Text size control

1. **CSS width/padding "size presets" (S/M/L)** — add a `text-size` concept via CSS
   classes that widen containers and add padding so blocks feel larger.
   - Pros: pure CSS, no engine/domain touch; trivially testable via Pilot.
   - Cons: cannot change glyph size (terminal limitation); "larger" is really
     "more whitespace + bolder". Misleads users who expect real zoom.
   - Effort: Low–Medium.
2. **Settings store + keybinding (e.g. +/-) cycling a `size` enum** — persist a
   preference in `progress.json` (new top-level `settings` key), apply a CSS class.
   - Pros: persistent, user-controlled, matches the app's JSON-store pattern.
   - Cons: still glyph-size-bound; adds a schema field (migration concern); needs UI.
   - Effort: Medium.
3. **Document that size is the terminal emulator's job** — add a help line / docs note
   pointing users to their terminal's zoom (Ctrl++), no code.
   - Pros: honest about the hard constraint; zero risk.
   - Cons: not a "feature"; users asking for in-app control get nothing.
   - Effort: Low.

**Recommendation (aspect 1)**: confirm with user what "text size control" must mean
given the terminal constraint. If in-app control is required, combine **2 + 3**: a
`settings` section with a size preset that adjusts CSS width/padding/bold, plus a docs
note explaining true zoom lives in the terminal. Do NOT promise pixel-level scaling.

### Aspect 2 — Text alignment / centering

1. **Center the practice block** — add `text-align: center` to `#practice-title`,
   `#practice-stats`, `#practice-text`.
   - Pros: one-line CSS each; visually consistent with `#results-body`; no logic change.
   - Cons: centered multi-line typing text can hurt the left-anchor rhythm touch-typists
     expect (cursor jumps column). May worsen UX for the practice text specifically.
   - Effort: Low.
2. **Center title/stats/keyboard, keep practice text left-aligned** — center the
   chrome, leave the target string left-justified (stable cursor column).
   - Pros: consistent chrome, preserves typing ergonomics; lowest-risk visual win.
   - Cons: mixed alignment within one screen (intentional, but must be documented).
   - Effort: Low.
3. **Make alignment a user setting** — store an `align` preference, toggle a CSS class.
   - Pros: user choice.
   - Cons: low value for the complexity; adds schema field + UI.
   - Effort: Medium.

**Recommendation (aspect 2)**: **Approach 2** — center `#practice-title`,
`#practice-stats`, and `#practice-keyboard`, leave `#practice-text` left-aligned.
Smallest, safest change; respects typing ergonomics. Verify the keyboard's per-row
stagger (`" " * row_index`) still reads correctly when its container is centered.

### Aspect 3 — Error handling & scoring

1. **Add a "forgiving" mode (wrong key still advances, marked as error)** — a second
   cursor model in `TypingSession`: on wrong key, record error AND advance.
   - Pros: matches some learners' preference (no being "stuck"); optional via flag.
   - Cons: breaks the documented edclub contract; `net_wpm`/`accuracy` semantics shift;
     many tests in `test_engine.py` pin the hold-cursor behavior — high test churn.
     Touches the most test-pinned, pure-domain module.
   - Effort: High (domain + tests + docs + a mode flag threaded through
     `PracticeScreen`/`Unit`).
2. **Let backspace clear the last recorded error** — `on_backspace` removes the most
   recent error entry when stepping back over an error position.
   - Pros: more forgiving accuracy without changing the cursor model.
   - Cons: contradicts `test_backspace_does_not_erase_recorded_errors`; changes the
     "errors are permanent" contract documented in engine.md.
   - Effort: Medium.
3. **Tune the star ladder / WPM gate only** — adjust `_STAR_ACCURACY_THRESHOLDS` or
   decouple the 4/5-star WPM gate.
   - Pros: small, surgical; isolated to `stars()` + one parametrized test.
   - Cons: only changes ratings, not "error handling".
   - Effort: Low.
4. **Keep the model, expose it as configurable** — make hold-vs-advance a per-unit or
     per-session policy.
   - Pros: flexibility.
   - Cons: same high test churn as #1 plus config plumbing.
   - Effort: High.

**Recommendation (aspect 3)**: this is the highest-risk area. Before proposing, confirm
which behavior the user wants to change: (a) the hold-cursor rule, (b) backspace error
erasure, or (c) only the scoring thresholds. Each has very different blast radius. The
engine is the most test-pinned module (13 tests) and is documented as the edclub
contract — any change here MUST be an opt-in mode, not a silent default flip, and MUST
update `docs/engineering/engine.md` + the star-ladder tests.

### Aspect 4 — Lesson unlock model

1. **Lower/raise the threshold** — change `>= 2` to `>= 1` or `>= 3` in `is_unlocked`.
   - Pros: one-line change; one test update.
   - Cons: only changes difficulty gating, not the model.
   - Effort: Low.
2. **Free navigation (unlock all)** — make `is_unlocked` always return True, or gate
   only reviews/speedtests.
   - Pros: user freedom; trivial.
   - Cons: removes the progression motivation; changes the lesson-map UX meaningfully.
   - Effort: Low.
3. **Non-sequential unlock** — unlock a unit when any of N previous units pass, or by
   accuracy instead of stars, or unlock reviews independently of lessons.
   - Pros: more flexible curriculum.
   - Cons: `is_unlocked` signature/semantics change; needs schema field if "unlocked
     via token" is persisted; test rewrite.
   - Effort: Medium.
4. **Persist explicit unlock/completion state** — add a `completed` flag and/or
   `unlocked` set to the JSON schema (bump `_SCHEMA_VERSION` → migration).
   - Pros: decouples unlock from stars; enables "skip" tokens, timestamps, etc.
   - Cons: schema migration (v1→v2); corrupt-file path + round-trip tests must be
     updated; reference/progress-schema.md rewrite.
   - Effort: Medium–High.

**Recommendation (aspect 4)**: clarify the desired model first. If the goal is just
"easier progression", **Approach 1** (threshold tweak) is the surgical win. If the goal
is "let users jump around", **Approach 2** or **3**. A schema bump (Approach 4) is only
worth it if unlock needs to diverge from stars — avoid unless required, because it
forces a migration and touches the corrupt-file/recovery contract.

---

## Recommendation (overall)

All four aspects are explorable, but they have very different risk profiles:

- **Low risk**: aspect 2 (alignment) — pure CSS, surgical, immediate visual win.
- **Low–Med risk**: aspect 4 threshold tweak (Approach 1) — one line + one test.
- **Medium risk**: aspect 1 (size) — bounded by the terminal-font hard constraint;
  needs a product decision on what "size control" means before building.
- **High risk**: aspect 3 (error/scoring) — touches the most test-pinned, documented
  contract in the codebase. Must be opt-in, not a default flip.

**Before proposal**: the user should state, per aspect, the *intended new behavior*.
Aspects 1 and 3 in particular are under-specified (terminal constraint for #1; which
of hold-cursor / backspace / thresholds for #3). Aspects 2 and 4 (threshold variant)
are ready to propose now.

## Risks

- **Terminal font-size hard constraint (aspect 1)**: an in-app "text size" feature
  cannot change glyph pixels — only layout/boldness. Promising real zoom will
  disappoint users and likely generate bug reports.
- **Edclub contract breakage (aspect 3)**: `engine.py` is the most test-pinned module
  (13 tests) and its hold-cursor rule is explicitly documented. A default change
  silently breaks the documented product identity. Any change MUST be opt-in.
- **Star-ladder / accuracy semantics (aspect 3)**: changing `on_backspace` or the
  hold-cursor rule shifts `accuracy`/`net_wpm` meaning, which feeds `stars()`,
  `record()` bests, and the unlock threshold — cascade across engine→progress→unlock.
- **Schema migration (aspect 4, Approach 4)**: bumping `_SCHEMA_VERSION` triggers the
  corrupt-file path for existing v1 files (users lose stars unless a migrator is
  added); the current code has NO migrator — it treats version mismatch as corruption.
- **Docs/changelog discipline (all aspects)**: AGENTS.md mandates doc-sync per module
  + a `[Unreleased]` CHANGELOG entry for every behavior change. Any proposal must
  budget for `docs/engineering/{engine,tui-screens,progress}.md`,
  `docs/reference/{cli,progress-schema}.md`, and `CHANGELOG.md`.
- **Keyboard stagger vs. centering (aspect 2)**: centering `#practice-keyboard` while
  it indents each row by `" " * row_index` may shift the visual center; verify in a
  Pilot snapshot before committing.

## Ready for Proposal

**Partially.** Aspects 2 and 4-threshold are ready to propose now. Aspects 1 and 3
need a product decision from the user first:
- Aspect 1: what should "text size control" do given terminals can't resize glyphs?
- Aspect 3: which behavior should change — hold-cursor rule, backspace error erasure,
  or only the star thresholds?

The orchestrator should ask the user these two questions before launching
`sdd-propose` for aspects 1 and 3.
