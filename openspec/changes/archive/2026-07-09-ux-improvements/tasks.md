# Tasks: UX Improvements

> Drives four specs under `openspec/changes/ux-improvements/specs/`. Slices land in
> dependency order 1→2→3→4. Architectures, formulas, and signatures live in
> `design.md` (§Interfaces, §Data Flow). TDD is strict: every code work unit is
> RED (failing test) → GREEN (implementation) → DOCS, committed together.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~500 total (PR 1 ~250, PR 2 ~250) |
| 400-line budget risk | Low (each PR individually under 400) |
| Chained PRs recommended | Yes (total exceeds 400) |
| Suggested split | PR 1 = slices 1-3 → PR 2 = slice 4 (stacked to main, in order) |
| Delivery strategy | force-chained (user-decided) |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | PR | Commit (Conventional, scoped) | Base |
|------|------|----|-------------------------------|------|
| W1 | Center all practice-screen elements (CSS) | PR 1 | `feat(tui): center title, stats, text, and keyboard` | main |
| W2 | Free navigation + idempotent v1→v2 migration + `settings` | PR 1 | `feat(progress): free lesson navigation with idempotent v1->v2 migration` | W1 |
| W3 | S/M/L text-size presets (consumes `settings`) | PR 1 | `feat(tui): add S/M/L text-size presets with plus/minus keybindings` | W2 |
| W4 | Forgiving error-model engine rewrite + cascade re-pin | PR 2 | `feat(engine): forgiving error model that advances on wrong key` | main (after PR 1 merges) |

**PR boundaries (BINDING):**
- **PR 1** = branch `ux/slices-1-3` off `main`, 3 commits (W1→W2→W3), merges to `main`. Lower risk, pure CSS + schema + UI wiring.
- **PR 2** = branch `ux/error-model` off `main` (rebased after PR 1 lands), 1 commit (W4), merges to `main`. Highest risk: engine rewrite + 13 test rewrites + 1 integration test.

**Dependency diagrams (include in each PR body per chained-pr skill):**
- PR 1: `main  ←  📍 PR 1 (ux/slices-1-3)`  — no parent.
- PR 2: `main  ←  📍 PR 2 (ux/error-model)`  — depends on PR 1 (W2 `settings` + `is_unlocked=True`); rebase on `main` before review.

---

## Phase 1 / Slice 1: Centered Layout (CSS only) — PR 1, W1

- [x] **1.1 RED** Create `tests/test_centered_layout.py`: async Pilot test `test_practice_elements_centered` opens unit 1, asserts `#practice-title/#practice-stats/#practice-text/#practice-keyboard` region properties show centered alignment (capture a committed snapshot string and assert equality). Add `test_centering_regression_fails_if_reverted` (flip a widget to left-align → assert snapshot differs) — runs red now.
- [x] **1.2 GREEN** In `src/tactile/styles.tcss`, add `text-align: center;` to `#practice-title`, `#practice-stats`, `#practice-text`, `#practice-keyboard`. Leave `Screen { align: center middle }` and `#results-body` untouched. Verify keyboard stagger (`widgets.py` `" " * row_index`) still reads centered via the snapshot; if lateral drift appears, document the escape hatch instead of changing widgets.py.
- [x] **1.3 DOCS** Update `docs/engineering/tui-screens.md`: record full centering + the ergonomics risk (cursor anchor column shifts per line) + the future left-align escape hatch (spec §Ergonomics Note). Add CHANGELOG `[Unreleased] → Added`: "Centered practice-screen layout (title, stats, text, keyboard)."
- [x] **Commit W1** `feat(tui): center title, stats, text, and keyboard` — test + css + docs together.

## Phase 2 / Slice 2: Free Lesson Navigation (schema v2 + unlock) — PR 1, W2

- [x] **2.1 RED** In `tests/test_progress.py` add (all run red against current `progress.py`):
  `test_fresh_store_is_v2_with_settings` (saved JSON has `"version": 2`, `"settings": {}`),
  `test_v1_file_migrates_to_v2_preserving_stars_and_key_errors` (write a v1 fixture `{"version":1,...}` with stars=4, key_errors={"f":12}; load → version 2, settings present, stars/key_errors preserved; a `.bak` of the v1 file exists),
  `test_migration_is_idempotent` (run migrator twice → byte-identical state),
  `test_v2_round_trip_preserves_settings_and_bests`,
  `test_any_lesson_is_attemptable` (`is_unlocked` True for index 0 and 9 with no progress),
  `test_completion_unlocks_all_previous_globally` (record ≥2 stars at unit 5 → `is_completion_unlocked` True for every index < 5; record 1 star elsewhere → no new unlocks),
  `test_corrupt_file_still_backed_up_and_not_treated_as_v1` (unparseable JSON → `.bak` rename + fresh v2, NOT migration).
  Invert existing `test_unlock_logic_first_unit_always_unlocked_second_needs_two_stars` → second unit now attemptable (True) without stars.
- [x] **2.2 GREEN** In `src/tactile/progress.py`:
  - `_SCHEMA_VERSION = 2`; `_default_state()` adds `"settings": {}`.
  - Add `import shutil`; add `_migrate_v1_to_v2(data)` (set `version=2`, `setdefault("settings", {})`, return data — idempotent, forward-only).
  - `_load()` branching: missing → default; unparseable/not-dict/unknown-future-version → `_backup_corrupt_file()` + fresh v2; `version` missing or `==1` → `_backup_v1_file()` (`shutil.copy2` → `.bak`, v1 NOT corrupt) + `_migrate_v1_to_v2(data)`; `version==2` → accept (defensive `setdefault("settings", {})`).
  - `is_unlocked(...)` → `return True`.
  - Add `is_completion_unlocked(layout_id, unit_index, units)`: `True iff unit_index==0 OR stars_for(units[unit_index].id)>=2 OR any(stars_for(units[j].id)>=2 for j in range(unit_index+1, len(units)))`.
  - Add `get_setting(key, default)` + `set_setting(key, value)` (`self._state.setdefault("settings", {})[key]=value; self._save()`).
- [x] **2.3 GREEN (UI wiring)** In `src/tactile/screens/lesson_map.py`: `disabled=not unlocked` → every row `disabled=False`; lock icon driven by `store.is_completion_unlocked(...)` (locked icon when completion-locked, space when unlocked). Keep `is_unlocked` for the "first highlighted" cursor only.
- [x] **2.4 DOCS** Update `docs/engineering/progress.md` + `docs/reference/progress-schema.md` (v2 schema with `settings`, migration semantics, `is_unlocked`/`is_completion_unlocked` distinction). CHANGELOG `[Unreleased]`: Added "Free lesson navigation — any lesson attemptable; ≥2 stars unlocks earlier lessons globally." Changed "Progress schema v1→v2 (adds `settings`); v1 files migrate losslessly with `.bak` backup."
- [x] **Commit W2** `feat(progress): free lesson navigation with idempotent v1->v2 migration`.

## Phase 3 / Slice 3: Text Size Control (consumes `settings`) — PR 1, W3

- [x] **3.1 RED** Create `tests/test_text_size.py` (async Pilot): `test_default_is_medium`, `test_plus_cycles_M_to_L`, `test_minus_cycles_L_to_M_to_S`, `test_cycling_wraps_at_both_ends`, `test_size_persists_across_restart` (set L → new app on same store → loads L), `test_invalid_stored_size_falls_back_to_M`. All run red (no bindings/class yet).
- [x] **3.2 GREEN (CSS)** In `src/tactile/styles.tcss` add `PracticeScreen.size-l #practice-title/stats/text/keyboard { width:96%; text-style: bold; }`, `PracticeScreen.size-s ... { width:80%; text-style: dim; }` (`size-m` = default 90% normal, no class). (Verify open Q: does `text-style:bold` bold `rich.Text` span runs in `#practice-text`? Check in Pilot; if not, bold the title/stats only and document.)
- [x] **3.3 GREEN (logic)** In `src/tactile/screens/practice.py`: `_SIZE_ORDER=("S","M","L")`; add `BINDINGS` `Binding("plus","cycle_size_up","Size +")`, `Binding("minus","cycle_size_down","Size -")`; `size_preset = reactive("M")`; `watch_size_preset` removes all `size-{s,m,l}` classes, adds `size-{preset.lower()}`, calls `self.store.set_setting("size", preset)`; `action_cycle_size_up`/`action_cycle_size_down` (mod-3 wrap). `on_mount`: load `store.get_setting("size","M")`, validate in {S,M,L} else "M", set `size_preset`. (Verify open Q: Textual key names `plus`/`minus` fire on Textual >=0.60 in the Pilot test.)
- [x] **3.4 DOCS** Update `docs/engineering/tui-screens.md` (size presets, width+weight semantics) + `docs/reference/keybinds.md` (`+`/`-` → Size up/down). CHANGELOG `[Unreleased]` Added "S/M/L text-size presets via `+`/`-`; persisted in `settings.size`; docs note presets change width+weight, not glyph pixels."
- [x] **Commit W3** `feat(tui): add S/M/L text-size presets with plus/minus keybindings`.

## Phase 4 / Slice 4: Forgiving Error Model (engine rewrite) — PR 2, W4

> Atomic, revertible commit. Highest risk. Order: rewrite `test_engine.py` (red) → rewrite `engine.py` (green) → rewrite the hold-cursor integration test → add cascade test → docs.

- [x] **4.1 RED (rewrite unit suite)** Rewrite `tests/test_engine.py` per design §Testing Strategy map. KEEP (signatures unchanged): `test_correct_key_advances`, `test_completion_and_stars`, `test_gross_wpm_counts_all_keystrokes_including_errors`, `test_stars_zero_when_incomplete`, `test_backspace_at_zero_is_noop`, `test_backspace_after_correct_char_requires_retyping_it`, `test_newline_matches_enter_char`, `test_metrics_are_zero_before_first_keystroke`, `test_extra_key_after_completion_is_ignored`. INVERT: `test_wrong_key_does_not_advance_and_records_error` → `test_wrong_key_advances_and_records_error` (position→1, `error_positions=={0:1}`, `key_errors=={"a":1}`); `test_backspace_does_not_erase_recorded_errors` → `test_backspace_erases_error_position_keeps_key_errors` (pop `error_positions[0]`, keep `key_errors`). ADD: `test_typing_past_errors_reaches_completion` ("hi"+"xy"→complete, errors {0,1}), `test_correction_yields_half_credit` (err→backspace→correct at 0 = 0.5 weight), `test_backspace_over_first_try_stays_first_try`, `test_accuracy_all_first_try_is_100`, `test_accuracy_one_corrected_four_char_is_87_5` (0.5+1+1+1)/4, `test_accuracy_one_uncorrected_four_char_is_75`, `test_live_accuracy_uses_attempted_so_far` (3/6 chars perfect → 100.0 live), `test_final_accuracy_uses_len_target`, `test_net_wpm_uses_credited_chars` (5 first-try +1 corrected over 1min → 1.1), `test_key_errors_persist_across_backspace`, `test_never_corrected_yields_zero_credit`. Rewrite the `stars` parametrize to construct sessions with exact first_try/corrected/uncorrected counts so accuracy is deterministic; thresholds `(90,95,97,99)` unchanged.
- [x] **4.2 GREEN** Rewrite `src/tactile/engine.py` `TypingSession` internals (signatures per design §engine.py): add `_ever_errored: set[int]`; remove `_correct_keystrokes`. `on_key(char)`: if complete return False; `_mark_first_keystroke`; expected=`_target[_position]`; `_total_keystrokes+=1`; if `char==expected`: `_position+=1`, return True; else `_ever_errored.add(_position)`, `_error_positions[p]+=1`, `_key_errors[expected]+=1`, `_position+=1`, return False. `on_backspace`: if `_position>0`: `_position-=1`; `_error_positions.pop(_position, None)` (`_ever_errored` persists; do NOT start timer). `_position_outcomes()` over `range(_position)`: `p in _ever_errored and p in _error_positions`→uncorrected; `p in _ever_errored and p not in _error_positions`→corrected; else first_try. `_credited_chars()=first_try+corrected*0.5`. `accuracy`: 100.0 if `_total_keystrokes==0` else `credited/total*100` where `total = len(_target) if is_complete else max(_position,1)`. `net_wpm=_wpm(_credited_chars())`; `_wpm` accepts float; `gross_wpm` unchanged. `stars` ladder unchanged, fed by new accuracy/net_wpm.
- [x] **4.3 GREEN (integration)** Rewrite `tests/test_practice_flow.py::test_wrong_key_does_not_advance_cursor` → `test_wrong_key_advances_and_records_error` (position advances by 1, expected moves forward, `session.error_positions` records the position). Add `test_error_to_accuracy_to_stars_to_record_to_unlock_cascade` (Pilot): type a unit with one mid error → results recorded, `store.stars_for` reflects new formula, lesson-map completion unlock reflects `is_unlocked` (always True). Keep `test_enter_on_results...` (stays green — `is_unlocked` True after slice 2).
- [x] **4.4 DOCS** Rewrite `docs/engineering/engine.md`: new error model (advance-on-wrong, backspace-erases), credited-accuracy formula, live-vs-final denominator, net_wpm char source, removed hold-cursor. CHANGELOG `[Unreleased]`: Added "Forgiving error model: wrong key advances; backspace erases recorded errors; corrected errors earn 0.5 partial credit." Changed "Accuracy weights positions (first-try 1.0, corrected 0.5, uncorrected 0.0); net WPM uses credited chars." Removed "Edclub hold-cursor error model."
- [x] **Commit W4** `feat(engine): forgiving error model that advances on wrong key` — tests + engine + integration + docs atomic.

---

## Changelog Block (target state under `[Unreleased]`)

**Added**
- Free lesson navigation — any lesson attemptable; ≥2 stars completes and unlocks earlier lessons globally.
- S/M/L text-size presets via `+`/`-` on the practice screen; persisted in `settings.size`.
- Forgiving error model: wrong key advances the cursor; backspace erases recorded errors; corrected errors earn 0.5 partial credit.
- Centered practice-screen layout (title, stats, text, keyboard).

**Changed**
- Progress schema v1→v2 (adds `settings`); v1 files migrate losslessly on load with a `.bak` backup.
- Accuracy weights positions (first-try 1.0, corrected 0.5, uncorrected 0.0); net WPM uses credited chars.

**Removed**
- Edclub hold-cursor error model (single replacement; no opt-in toggle).

---

## Review Guide (for the human reviewer — you wanted to learn this)

**Per PR — what "done" looks like (acceptance criteria from specs):**
- **PR 1**: `uv run python -m pytest -q` green; `+`/`-` cycles S→M→L and wraps both ways; size persists across restart and falls back to M on invalid; any lesson openable with no prior progress; completing ≥2 stars shows earlier lessons unlocked in the map; v1 file migrates (stars preserved, `.bak` created, idempotent); title/stats/text/keyboard visually centered (snapshot matches).
- **PR 2**: wrong key advances + records `error_positions` + `key_errors`; backspace pops that error but keeps `key_errors`; corrected position = 0.5 credit; one-corrected-4-char=87.5%, one-uncorrected-4-char=75%, all-first-try=100%; live accuracy uses attempted-so-far, final uses `len(target)`; net_wpm from credited chars (5+1 corrected/1min=1.1); star ladder `(90/95/97/99)` unchanged; full cascade error→acc→stars→record→unlock re-pinned; no hold-cursor test remains.

**How to review locally (before approving):**
```sh
# 1. Fetch the PR (replace <N>)
gh pr checkout <N>
# 2. Tests must be green (NOTE: -m form, not `uv run pytest`)
uv run python -m pytest -q
# 3. Docs links must resolve
uv run python scripts/validate_docs.py
# 4. See the story each commit tells
git log --oneline main..HEAD
git diff --stat main..HEAD
```

**How to review on GitHub (`gh pr review`):**
```sh
gh pr view <N>                       # read title/body/dependency diagram
gh pr diff <N>                       # full diff in terminal
gh pr checks <N>                     # CI status
gh pr review <N> --request --body "question on …"   # request changes
gh pr review <N> --approve --body "LGTM: …"          # approve
gh pr merge <N> --squash              # only after approval (PR 1 first)
```
On the web UI: open "Files changed", use the per-commit view to read one work unit at a time (W1/W2/W3 in PR 1; W4 in PR 2). Each commit should stand alone and pass tests.

**Review order matters:** review and merge **PR 1 first** (it lands the `settings` block + `is_unlocked=True` that PR 2's cascade test depends on). After PR 1 merges, rebase PR 2 onto `main` so its diff shows only engine work (if you see CSS/progress changes in PR 2's diff, the base is wrong — retarget/rebase).

**Commit-organization check (work-unit-commits skill):** each commit = one behavior + its tests + its docs together. Red flag: a commit named "add tests" or "update docs" alone (docs/tests must ride with the behavior). Each PR's commits here follow that rule.

**Per-PR focus checklist:**
- [ ] PR 1: diff reads as three independent slices (W1 centering, W2 schema+unlock, W3 size). No engine.py changes. ≤~250 lines.
- [ ] PR 2: only `engine.py` + `tests/test_engine.py` + `tests/test_practice_flow.py` + `docs/engineering/engine.md` + CHANGELOG. ≤~250 lines. Engine commit is atomic (revertible alone).
