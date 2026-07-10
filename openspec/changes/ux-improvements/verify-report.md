# Verification Report: UX Improvements

- **Change**: `ux-improvements` (4 capabilities, 2 PRs merged to `main`)
- **Mode**: Strict TDD — runtime evidence required for every spec scenario
- **Persistence**: Hybrid (Engram + OpenSpec file)
- **Verdict**: **PASS WITH WARNINGS** — every spec requirement has passing runtime evidence; one doc-sync WARNING + one doc-quality SUGGESTION (neither blocks archive)

## Build / Tests / Coverage Evidence

| Command | Result |
|---|---|
| `uv run python -m pytest -q` | **103 passed, 0 failed** (matches the expected 103) |
| `uv run python scripts/validate_docs.py` | **OK — 23 wikilink(s) resolved** |
| Hold-cursor remnants in `src/` | None. The single `hold-cursor` hit in `engine.py:40` is an explanatory comment ("the structural difference from the old hold-cursor model"), not a code path or toggle. |

Commits on `main` (feature-classified, scoped, atomic — matches tasks.md W1→W2→W3→W4):
```
122bc45 feat(engine): forgiving error model that advances on wrong key   # PR 2 / W4
410d920 feat(tui): add S/M/L text-size presets with plus/minus keybindings # PR 1 / W3
96acf5c feat(progress): free lesson navigation with idempotent v1->v2 migration # PR 1 / W2
3e1664d feat(tui): center title, stats, text, and keyboard               # PR 1 / W1
```

## Completeness Table

| Dimension | Artifacts present | Status |
|---|---|---|
| Proposal | `proposal.md` | ✅ Read |
| Specs (×4) | `specs/{centered-layout,free-lesson-navigation,text-size-control,forgiving-error-model}/spec.md` | ✅ All read, every scenario mapped |
| Design | `design.md` | ✅ Read; design decisions honored |
| Tasks | `tasks.md` | ⚠️ See note below |
| Implementation | 6 source files + 4 test files | ✅ Inspected |
| CHANGELOG | `[Unreleased]` Added/Changed/Removed | ✅ All 4 capabilities present |

> **Tasks.md checkbox state is stale.** Slice 4 checkboxes (4.1–4.4) are still `[ ]` even though commit `122bc45` fully delivers W4 (engine rewrite + integration + docs). This is a bookkeeping drift in the task list, NOT an incomplete task — the work is done, committed, and green. **SUGGESTION**: tick 4.1–4.4 before archiving so the task list reflects reality.

## Spec Compliance Matrix

### 1. Centered Layout — ✅ FULLY COMPLIANT

| Requirement / Scenario | Implementation evidence | Covering test (passing) |
|---|---|---|
| `#practice-title/stats/text/keyboard` → `text-align: center` | `styles.tcss:12-35` (all four selectors set `text-align: center`); containers stay centered via `Screen { align: center middle }` | `test_practice_widgets_resolve_centered_text_align` |
| Keyboard stagger stays centered | `widgets.py:59` `" " * row_index` unchanged; resolves to center | same test covers `#practice-keyboard` |
| Results screen unchanged | `#results-body` untouched (60% + center) | `test_results_body_remains_centered` |
| Centering regression is caught | Test asserts resolved `styles.text_align == "center"`; a left-align revert fails it | `test_centered_layout.py` |
| Ergonomics note + escape hatch (SHOULD/MAY) | `docs/engineering/tui-screens.md` §"Ergonomics note (cursor anchor shift)" (lines 274-287) | doc review |

### 2. Free Lesson Navigation — ✅ FULLY COMPLIANT

| Requirement / Scenario | Implementation evidence | Covering test (passing) |
|---|---|---|
| `is_unlocked` always True | `progress.py:154-161` returns `True` | `test_unlock_logic_any_lesson_is_attemptable` (all 10 indices) |
| First + later lesson attemptable | same | same |
| `is_completion_unlocked` ∃j>i cascade | `progress.py:163-184`: index 0 OR stars≥2 OR any later j has stars≥2 | `test_completion_unlocks_all_previous_globally` |
| Completing later marks earlier unlocked | completing index 5 → every index<5 True | same |
| Below 2 stars → no change | 1 star recorded → no new unlocks | same |
| Schema v2 + `settings: {}` | `_default_state` v2 + settings; `_SCHEMA_VERSION=2` | `test_fresh_store_is_v2_with_settings` |
| Per-lesson bests shape unchanged | `record()` max-preservation + key_errors accumulate | `test_v2_round_trip_preserves_settings_and_bests` |
| v1→v2 preserves stars/key_errors | `_migrate_v1_to_v2` + `_backup_v1_file` (`shutil.copy2`) | `test_v1_file_migrates_to_v2_preserving_stars_and_key_errors` (+ `.bak` exists) |
| Migration idempotent | `_migrate_v1_to_v2` is setdefault-based | `test_migration_is_idempotent` (byte-identical) |
| Round-trip preserves state | save+reload | `test_v2_round_trip_preserves_settings_and_bests` |
| Corrupt file still backed up, NOT treated as v1 | `_load` corrupt branch → rename `.bak` + fresh v2 | `test_corrupt_file_still_backed_up_and_not_treated_as_v1` |
| Lesson-map lock icon from `is_completion_unlocked`; rows never disabled | `screens/lesson_map.py:51-58` | `test_lesson_map_all_rows_clickable_and_lock_icon_reflects_completion` |

### 3. Text Size Control — ✅ FULLY COMPLIANT

| Requirement / Scenario | Implementation evidence | Covering test (passing) |
|---|---|---|
| Exactly S/M/L presets; width + weight each | `_SIZE_ORDER` + `styles.tcss` size-l (96% bold), size-s (80% dim), size-m base (90% normal) | `test_plus_cycles_medium_to_large`, `test_minus_cycles_large_down_to_small` |
| M default on first launch | `practice.py:75-78` on_mount | `test_default_is_medium` |
| `+` cycles M→L (widens, bolds) | `action_cycle_size_up` + class swap | `test_plus_cycles_medium_to_large` (asserts `size-l`) |
| `-` cycles L→M→S (narrows, dims) | `action_cycle_size_down` | `test_minus_cycles_large_down_to_small` |
| Wrap both ends (S→L, L→S) | mod-3 arithmetic | `test_cycling_wraps_at_both_ends` |
| Persists across restart | `watch_size_preset` → `set_setting("size", preset)` | `test_size_persists_across_restart` |
| Invalid stored value → M fallback | `practice.py:76-77` validates `{S,M,L}` | `test_invalid_stored_size_falls_back_to_medium` |
| Zoom-constraint note (in-app help + tui-screens.md) | `keybinds.md:13-14`; `tui-screens.md:128-130` | doc review |

### 4. Forgiving Error Model (highest risk) — ✅ FULLY COMPLIANT

| Scenario (spec) | Implementation evidence | Covering test (passing) |
|---|---|---|
| Wrong key advances + records error | `engine.py:103-120` (record `_ever_errored`+`_error_positions`+`_key_errors`, `_position+=1`) | `test_wrong_key_advances_and_records_error` |
| Typing past errors reaches completion | same | `test_typing_past_errors_reaches_completion` ("hi"+"xy"→done, errors {0,1}) |
| Backspace erases recorded error (NOT `_ever_errored`) | `engine.py:122-130` pops `_error_positions`, leaves `_ever_errored` + `_key_errors` | `test_backspace_erases_error_position_keeps_key_errors` |
| Backspace over first-try-correct position | same | `test_backspace_over_first_try_stays_first_try` |
| Correction → 0.5 partial credit | `_position_outcomes` + `_credited_chars` | `test_correction_yields_half_credit` |
| Never-corrected → 0.0 credit | same | `test_never_corrected_yields_zero_credit` |
| All first-try = 100% | `accuracy` property | `test_accuracy_all_first_try_is_100` |
| One corrected, 4-char = 87.5% | `accuracy` | `test_accuracy_one_corrected_four_char_is_87_5` |
| One uncorrected, 4-char = 75.0% | `accuracy` | `test_accuracy_one_uncorrected_four_char_is_75` |
| Live accuracy uses `max(position,1)` | `engine.py:88` | `test_live_accuracy_uses_attempted_so_far` (3/6→100) |
| Final accuracy uses `len(target)` | `engine.py:88` | `test_final_accuracy_uses_len_target` |
| net_wpm uses credited chars (5+1 corrected/1min=1.1) | `net_wpm` → `_wpm(_credited_chars())` | `test_net_wpm_uses_credited_chars` |
| net_wpm + gross_wpm = 0.0 pre-timer | `_wpm` guard | `test_metrics_are_zero_before_first_keystroke` |
| Stars use new accuracy, same thresholds (90/95/97/99) | `stars()` unchanged ladder, feeds new acc/net | `test_stars_ladder_boundaries_driven_by_accuracy` (9 cases) + `test_completion_and_stars` |
| Record persists new bests (max) | `record()` max-preservation | `test_record_keeps_best_stars_and_wpm_but_still_accumulates_key_errors` |
| Old hold-cursor removed (no toggle/path) | no `toggle`/`hold_cursor` code; single model | full rewritten `test_engine.py` — no hold-cursor assertion remains |
| Full cascade error→acc→stars→record→unlock | integration Pilot | `test_error_to_accuracy_to_stars_to_record_to_unlock_cascade` |

## Correctness Table (cascade consistency)

The internal cascade `error → _ever_errored → _position_outcomes → accuracy → net_wpm → stars → record` is internally consistent: `stars()` and `_finish_exercise()`/`record()` read the SAME `self.accuracy` and `self.net_wpm` properties (verified `practice.py:128-163`, `engine.py:158-173`). No divergent computation found.

## Test-Impact Audit (Engram #325) — ✅ FULLY ADDRESSED

| Breaking test (per audit) | Resolution |
|---|---|
| `test_wrong_key_does_not_advance_and_records_error` | rewritten → `test_wrong_key_advances_and_records_error` |
| `test_accuracy_with_mixed_correct_and_wrong_attempts` | rewritten → `test_accuracy_with_mixed_correct_uncorrected_and_corrected` |
| `test_gross_wpm_counts_all_keystrokes_including_errors` | adapted (now completes with fewer keystrokes) |
| `test_stars_ladder_boundaries_driven_by_accuracy` | rewritten (constructs exact first-try/corrected/uncorrected) |
| `test_backspace_does_not_erase_recorded_errors` | inverted → `test_backspace_erases_error_position_keeps_key_errors` |
| `test_practice_flow.py::test_wrong_key_does_not_advance_cursor` | rewritten → `test_wrong_key_advances_and_records_error` |
| `test_progress.py` is_unlocked False→True | rewritten → `test_unlock_logic_any_lesson_is_attemptable` |
| `test_app.py:39` is_unlocked False→True | rewritten → `test_fresh_store_unlocks_only_first_lesson` (+ lock-icon test) |

All 8 audited breakage points (6 engine/flow + 2 unlock) rewritten and green.

## Issues

### CRITICAL
*(none)*

### WARNING
1. **`docs/reference/keybinds.md` "Typing keys" table describes the OLD hold-cursor model.**
   - `keybinds.md:27` — "Advance if correct; otherwise record an error and **stay**." → the forgiving model now ADVANCES on a wrong key.
   - `keybinds.md:29` — backspace "Does **not** erase recorded errors." → backspace now ERASES `_error_positions` (the `_key_errors` heatmap persists, but the recorded position error is popped).
   - **Impact**: AGENTS.md makes documentation-sync MANDATORY; this user-facing reference contradicts shipped + tested behavior. No spec scenario or test fails (the authoritative `docs/engineering/engine.md` is correct), so it does not block archive — but it should be fixed (2-line edit) before or as a fast-follow to archive.
   - Note: the "does not erase recorded errors" hit in `docs/decisions/plans/2026-07-08-touchtype-tui.md` is an immutable historical decision record (pre-change) and is NOT a violation.

### SUGGESTION
1. **`docs/reference/progress-schema.md` duplicates the "## Per-layout object" section** (lines 24-41 and 58-75 are byte-identical). Collapse to one. Cosmetic doc-quality fix.
2. **`tasks.md` slice-4 checkboxes (4.1–4.4) are still `[ ]`** though W4 is fully delivered by commit `122bc45`. Tick them before archiving so the task log matches reality.

## Final Verdict

**PASS WITH WARNINGS.** All 4 capabilities meet every MUST/SHOULD requirement with passing runtime evidence (103/103 tests green; docs validate). The forgiving error model — the highest-risk capability — is precisely implemented and exhaustively tested against every spec scenario, including the exact 87.5% / 75.0% / 1.1-wpm cases and the live-vs-final denominator. The single WARNING is a 2-line doc-sync gap in `keybinds.md` that does not affect runtime correctness or any spec scenario.

## Next Step
- `next_recommended`: **archive** (no CRITICALs). Recommended pre-archive polish: fix the `keybinds.md` "Typing keys" drift (WARNING #1), tick slice-4 task boxes, and de-duplicate the progress-schema section (SUGGESTIONs). None of these block the archive gate.
