# Proposal: UX Improvements

> Source: `openspec/changes/ux-improvements/exploration.md` + Engram `sdd/ux-improvements/explore` (#309).
> Four product decisions are BINDING (see Assumptions). Aspect numbering follows the exploration: 1=text size, 2=centering, 3=error handling, 4=unlock/skip.

## Intent

Four UX changes to give learners flexibility, accessibility, and control: adjustable text "size", a forgiving error/scoring model, free lesson navigation, and a fully centered UI. Today the app is rigid — left-aligned chrome, no size control, a strict edclub "hold cursor" error model, and strictly sequential unlocks — which underserves learners who need bolder text, who outpace the sequence, or who prefer to type past mistakes.

## Scope

### In Scope
- **Text size (1):** S/M/L presets via in-app `+`/`-` keybindings; each level adjusts container width + text weight (bold for L, light for S); persisted in settings.
- **Error model (3):** wrong key advances cursor + records error; backspace erases the recorded error at that position; dynamic scoring with partial credit (~50%, placeholder) for later-corrected errors.
- **Skip lessons (4):** any lesson attemptable; completing (≥2 stars) unlocks ALL previous lessons across ALL units; schema v1→v2 migration preserving stars/key_errors.
- **Centering (2):** title, stats, keyboard, AND practice text centered.

### Out of Scope
- New curriculum content / new lessons / wordlist format changes / new screens.
- Real glyph/font-pixel zoom (terminal limitation — documented, not built).
- Multiple opt-in cursor-model strategies (single new model replaces edclub hold-cursor).

## Capabilities

> `openspec/specs/` is empty (no baseline specs). sdd-spec creates all as new `spec.md` files; items marked *modifies* cover behavior already in code that this change alters.

### New Capabilities
- `text-size-control`: S/M/L presets via keybinding + persisted setting; width+weight adjustment. (new)
- `typing-engine`: `TypingSession` on_key/on_backspace, accuracy, net_wpm, stars. *modifies existing* — advances-on-error, backspace-erases-errors, dynamic scoring w/ partial credit.
- `lesson-progression`: `is_unlocked`, `record`, schema, migrator. *modifies existing* — free navigation + global unlock-on-complete + v1→v2 migration.
- `practice-ui`: `styles.tcss` alignment + widgets. *modifies existing* — full centering.

### Modified Capabilities
None — `openspec/specs/` has no baseline specs; see New Capabilities above.

## Approach

| # | Change | Approach | Key files / funcs |
|---|--------|----------|-------------------|
| 1 | Text size | `settings` block in progress JSON (`size`: S/M/L); `+`/`-` bindings in `PracticeScreen` apply a CSS class (`size-s/m/l`) controlling container `width` + `text-style`. Persist via `ProgressStore`. | `styles.tcss`; `screens/practice.py` (bindings, `_refresh_text`); `progress.py` (`_default_state`, `record`); `app.py` |
| 3 | Error model | Rewrite `on_key`: wrong char → record error + advance. `on_backspace`: step back AND remove the error entry at that position. Scoring: corrected error = ~50% credit; `accuracy`/`net_wpm` recomputed from correct + credited. Star ladder thresholds preserved. **Cascade to re-pin: error → accuracy → stars → record → unlock.** | `engine.py` (`on_key`, `on_backspace`, `accuracy`, `net_wpm`, `stars`); `docs/engineering/engine.md` |
| 4 | Skip lessons | Bump `_SCHEMA_VERSION` 1→2; add forward-only migrator in `progress.py` carrying `stars`/`best_wpm`/`best_acc`/`key_errors` verbatim + adding `settings: {}`. `is_unlocked`: any lesson attemptable; ≥2 stars on completion unlocks all previous across all units. | `progress.py` (`is_unlocked`, `record`, `_SCHEMA_VERSION`, migrator); `screens/lesson_map.py`; `docs/reference/progress-schema.md` |
| 2 | Centering | `text-align: center` on `#practice-title`, `#practice-stats`, `#practice-text`, `#practice-keyboard`. Verify keyboard stagger indent (`" " * row_index`) still centers cleanly via Pilot snapshot. | `styles.tcss`; `widgets.py` (`_render_keyboard`) |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/tactile/engine.py` | Modified | on_key/on_backspace/accuracy/stars rewrite (high test churn) |
| `src/tactile/progress.py` | Modified | schema v2 + migrator + `is_unlocked` rewrite |
| `src/tactile/styles.tcss` | Modified | centering + size-preset classes |
| `src/tactile/screens/practice.py` | Modified | keybindings, settings load, `_refresh_text` |
| `src/tactile/screens/lesson_map.py` | Modified | free-navigation display |
| `src/tactile/widgets.py` | Modified | keyboard centering verify |
| `src/tactile/app.py` | Modified | bindings wiring |
| `tests/test_engine.py` | Modified | rewrite ~13 pinning tests |
| `tests/test_progress.py` | Modified | unlock + migrator tests |
| docs + `CHANGELOG.md` | Modified | per AGENTS.md mapping |

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| **Terminal cannot resize glyphs (1)** — users expect real zoom | High | Document explicitly (help line + `tui-screens.md`): "size" = width+weight perception, not pixel zoom; point to terminal Ctrl+ zoom. Do not promise scaling. |
| **Engine test cascade (3)** — 13 tests pin hold-cursor; `accuracy`/`net_wpm`/`stars`/unlock semantics shift | High | TDD red→green rewrite of `test_engine.py`; re-pin the full cascade error→accuracy→stars→record→unlock; update `docs/engineering/engine.md`. |
| **Schema migration data loss (4)** — no migrator exists; v1 is currently treated as corruption (rename `.bak`, start fresh) → users lose stars | High | Idempotent v1→v2 migrator carrying stars/bests/key_errors; add round-trip + migration tests; never default to "fresh" for a known v1. Backup `progress.json` before first v2 write. |
| Centered practice text hurts typing ergonomics (cursor column jumps) + keyboard stagger shifts visual center (2) | Medium | Pilot snapshot before/after; keep option to revert practice text to left if it degrades UX. |
| Correction credit (~50%) is a guess (3) | Medium | Mark as placeholder; refine to a concrete formula in spec. |

## First Slice (recommended order — lowest risk first)

1. **Centering (2)** — CSS-only, no domain/tests touched, immediate visual win.
2. **Text size (1)** — bounded by terminal constraint; CSS + small settings field.
3. **Skip lessons (4)** — schema migration (migrator + tests) but isolated to `progress.py`.
4. **Error model (3)** — riskiest; do last with full TDD rewrite of engine tests.

## Assumptions

- Correction credit ≈ 50% of a first-try correct is a placeholder to refine in spec.
- "Unlock all previous across all units" = completing ANY lesson with ≥2 stars unlocks every lesson with a lower index across ALL units (global, not per-unit).
- Schema v2 adds a `settings` object; existing v1 files migrate losslessly.
- The new error model REPLACES the edclub hold-cursor model (single model, not an opt-in toggle) — per binding decision.

## Rollback Plan

- Each change lands as its own atomic Conventional Commit (scoped `tui`/`engine`/`progress`/`layouts`); revert the commit to roll back a slice.
- **Centering / size (2,1):** pure CSS + settings — revert commits; no data impact.
- **Error model (3):** revert `engine.py` commit + restore `tests/test_engine.py`; progress data unaffected (scoring is runtime; only bests persist).
- **Schema v2 (4):** migrator is forward-only; on rollback, revert the `_SCHEMA_VERSION` gate. Backup `progress.json` before first v2 write; keep the v1 `.bak` path intact as a safety net.

## Dependencies

- None external. All changes within `src/tactile/` + tests + docs.

## Success Criteria

- [ ] `uv run python -m pytest -q` green with rewritten engine/progress tests.
- [ ] `+`/`-` cycles S/M/L, persists across restart, adjusts width+weight; docs note the terminal-zoom limit.
- [ ] Wrong key advances + records error; backspace erases that error; corrected error yields partial credit; cascade (accuracy→stars→record→unlock) re-pinned.
- [ ] Any lesson attemptable; ≥2 stars unlocks all previous across all units; v1 file migrates losslessly (stars preserved).
- [ ] Title/stats/keyboard/practice-text centered; Pilot snapshot confirms no stagger regression.
- [ ] Docs (engine/tui-screens/progress/cli/progress-schema) + `CHANGELOG.md` `[Unreleased]` updated; `scripts/validate_docs.py` passes.
