# Design: UX Improvements

> Drives `openspec/changes/ux-improvements/specs/{text-size-control,centered-layout,forgiving-error-model,free-lesson-navigation}/spec.md`. Resolves the three open questions from the spec phase (see Architecture Decisions).

## Technical Approach

Four capabilities delivered as four atomic slices in dependency order: **centered-layout** (CSS) → **free-lesson-navigation** (schema v2 + `settings` + unlock) → **text-size-control** (consumes `settings`) → **forgiving-error-model** (engine rewrite, replaces hold-cursor). The engine rewrite is last: it is the most test-pinned module and its scoring cascade (error→accuracy→net_wpm→stars→record→unlock) must be re-pinned against the new formulas. No feature flag — the spec mandates a single replacement model (`MUST NOT retain a hold-cursor path or opt-in toggle`).

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|---|---|---|---|
| Schema field name (Q3) | `version` (existing) | `schema_version` | `progress.py:18,23` uses `version`. Spec field name confirmed against code. |
| net_wpm char source (Q1) | `credited = first_try + corrected*0.5` | `position` | Spec: net_wpm from credited chars. Old `position`==correct-count no longer holds (wrong key now advances). Time formula `(chars/5)/minutes` unchanged; only char source changes. |
| accuracy denominator | `len(target)` (literal spec) | `_position` | Spec: `total_positions = len(target)`. Mid-session ACC climbs from 0% — flagged as risk. |
| Attemptable vs display (Q2) | two methods | single `is_unlocked` | `is_unlocked`→always True (clickable, no disabled rows); `is_completion_unlocked`→derived lock-icon badge. Reconciles "always attemptable" + "completion unlocks previous". |
| Completion persistence | derived from `stars>=2` | `completed` bool list | Spec: "no separate completed_lessons list required". Minimal schema (only `settings` added). |
| Backspace erasure | pop `error_positions[p]`; keep `key_errors` + `_ever_errored` | erase all | Spec erases `error_positions` only; `key_errors` is the cumulative heatmap; `_ever_errored` drives corrected-credit. |
| Text size storage | `settings.size` in progress JSON | separate file | Matches existing JSON-store pattern; rides v2 schema. |
| Engine model | single replacement, no toggle | opt-in flag | Spec binding. Contradicts exploration's "opt-in" recommendation; spec wins. |
| v1 backup | COPY to `.bak` at load | rename (move) | Preserves v1 until v2 write succeeds; safe if save never fires. |

## Data Flow

Scoring cascade (new):
```
on_key(wrong)  -> _ever_errored.add(p); _error_positions[p]+=1; _key_errors[exp]+=1; _position+=1; return False
on_key(correct)-> _position+=1; return True           (status derived from _ever_errored at query)
on_backspace   -> if position>0: position-=1; _error_positions.pop(position)   (_ever_errored persists)
accuracy       -> (first_try*1.0 + corrected*0.5) / len(target) * 100          [no keystrokes -> 100.0]
net_wpm        -> ((first_try + corrected*0.5)/5)/minutes                       [pre-timer -> 0.0]
gross_wpm      -> (total_keystrokes/5)/minutes                                   [unchanged]
stars          -> ladder (90/95/97/99) on new accuracy + net_wpm                 [thresholds unchanged]
record         -> max-best stars/best_wpm/best_acc + accumulate key_errors       [contract unchanged]
unlock         -> is_unlocked=True; is_completion_unlocked derived from stars>=2 frontier
```

## Interfaces / Contracts

### engine.py — `TypingSession` (rewritten internals)
```python
class TypingSession:
    def __init__(self, target, clock=time.monotonic):
        self._target=target; self._clock=clock
        self._position=0; self._start_time=None
        self._total_keystrokes=0
        self._error_positions: dict[int,int] = {}   # current count per position; popped on backspace
        self._key_errors: dict[str,int] = {}        # cumulative heatmap; never erased
        self._ever_errored: set[int] = set()        # persists across backspace -> drives corrected credit
    def on_key(self, char: str) -> bool: ...        # wrong: record+advance, return False; correct: advance, return True
    def on_backspace(self) -> None: ...             # if position>0: position-=1; _error_positions.pop(position)
    @property
    def accuracy(self) -> float: ...                # 100.0 if no keystrokes else credited/len(target)*100
    @property
    def net_wpm(self) -> float: ...                 # _wpm(credited)
    @property
    def gross_wpm(self) -> float: ...               # _wpm(total_keystrokes)  [unchanged]
    def stars(self, wpm_target: float) -> int: ...  # unchanged ladder, new acc/net
    def _position_outcomes(self) -> tuple[int,int,int]:  # (first_try, corrected, uncorrected) over range(position)
    def _credited_chars(self) -> float:                  # first_try + corrected*0.5
```
Position-outcome rule — for `p` in `range(self._position)`:
- `p in _ever_errored` and `p in _error_positions` → **uncorrected** (0.0)
- `p in _ever_errored` and `p not in _error_positions` → **corrected** (0.5)
- else → **first-try-correct** (1.0)

State machine: `idle` (no keystrokes) → `typing` (on_key/on_backspace) → `done` (`is_complete`). Error/backspace/correction are transitions within `typing`. `on_backspace` no longer starts the timer (only `on_key` does).

### progress.py — schema v2 + settings + unlock
```python
_SCHEMA_VERSION = 2
def _default_state() -> dict: return {"version": 2, "active_layout": None, "layouts": {}, "settings": {}}
def _migrate_v1_to_v2(data: dict) -> dict:      # idempotent, forward-only
    data["version"] = 2
    data.setdefault("settings", {})
    return data                                  # layouts/lessons/key_errors preserved verbatim

class ProgressStore:
    def is_unlocked(self, layout_id, unit_index, units) -> bool: return True   # any lesson attemptable
    def is_completion_unlocked(self, layout_id, unit_index, units) -> bool:
        # True iff unit_index==0 OR stars_for(unit_index)>=2
        #      OR any unit j>unit_index has stars_for>=2  (completion cascade unlocks lower indices)
    def get_setting(self, key: str, default): ...
    def set_setting(self, key: str, value) -> None:
        self._state.setdefault("settings", {})[key] = value; self._save()
```
`_load` branching:
- file missing → `_default_state()` (v2)
- unparseable / not a dict / unknown future version → `_backup_corrupt_file()` (existing rename) + fresh v2
- `version` missing or `== 1` → `_backup_v1_file()` (`shutil.copy2` → `.bak`, v1 NOT treated as corrupt) + `_migrate_v1_to_v2(data)`
- `version == 2` → accept (defensive `setdefault("settings", {})`)

**Idempotency proof**: `_migrate_v1_to_v2` on already-v2 data sets `version=2` (no-op) and `setdefault("settings", {})` (no-op if present); the returned dict is byte-identical to the input. Re-running yields identical state. ✓

### styles.tcss — centering + size presets
```css
#practice-title, #practice-stats, #practice-text, #practice-keyboard { text-align: center; }

PracticeScreen.size-l #practice-title,
PracticeScreen.size-l #practice-stats,
PracticeScreen.size-l #practice-text,
PracticeScreen.size-l #practice-keyboard { width: 96%; text-style: bold; }

PracticeScreen.size-s #practice-title,
PracticeScreen.size-s #practice-stats,
PracticeScreen.size-s #practice-text,
PracticeScreen.size-s #practice-keyboard { width: 80%; text-style: dim; }
/* size-m = default (90%, normal weight) — no class */
```
Keyboard stagger (`" " * row_index` in `widgets.py:59`) + `text-align: center`: each row centers independently. Verify no lateral drift via Pilot snapshot; escape hatch = leave `#practice-keyboard` left-aligned if drift (documented in `tui-screens.md`).

### screens/practice.py — keybindings + reactive size + error rendering
```python
_SIZE_ORDER = ("S", "M", "L")

class PracticeScreen(Screen):
    BINDINGS = [
        Binding("escape", "back_to_map", "Back to map"),
        Binding("plus", "cycle_size_up", "Size +"),
        Binding("minus", "cycle_size_down", "Size -"),
    ]
    size_preset = reactive("M")
    def watch_size_preset(self, preset: str) -> None:
        for s in _SIZE_ORDER: self.remove_class(f"size-{s.lower()}")
        self.add_class(f"size-{preset.lower()}")
        self.store.set_setting("size", preset)
    def action_cycle_size_up(self) -> None:   # S->M->L->S
        i = _SIZE_ORDER.index(self.size_preset); self.size_preset = _SIZE_ORDER[(i + 1) % 3]
    def action_cycle_size_down(self) -> None: # S->L->M->S
        i = _SIZE_ORDER.index(self.size_preset); self.size_preset = _SIZE_ORDER[(i - 1) % 3]
    # on_mount: load store.get_setting("size","M"); validate in {S,M,L} else "M"; set size_preset
```
`_refresh_text` rewrite: render `target[:position]` **per char** — error positions (`p in session.error_positions`) → style `"red"`, others → `"green"`; cursor char at `position` → `"reverse"`; rest → `"dim"`. The `_last_key_was_wrong` flag becomes optional (errors are always shown red).

## File Changes

| File | Action | Description |
|---|---|---|
| `src/tactile/styles.tcss` | Modify | `text-align:center` on 4 widgets; add `size-s`/`size-l` classes |
| `src/tactile/engine.py` | Modify | advances-on-error; backspace erases `error_positions`; `_ever_errored` set; credited accuracy/net_wpm |
| `src/tactile/progress.py` | Modify | `_SCHEMA_VERSION=2`; migrator; `is_unlocked=True`; `is_completion_unlocked`; `get/set_setting`; v1 backup-copy |
| `src/tactile/screens/practice.py` | Modify | size reactive + `plus`/`minus` bindings; `_refresh_text` per-char error coloring |
| `src/tactile/screens/lesson_map.py` | Modify | `disabled=False` always; lock icon from `is_completion_unlocked` |
| `src/tactile/widgets.py` | Modify | verify keyboard centering only (no logic change) |
| `tests/test_engine.py` | Modify | rewrite ~13 → ~16 tests for new model |
| `tests/test_progress.py` | Modify | migration, idempotency, round-trip, any-attemptable, completion-unlock, settings fallback |
| `tests/test_centered_layout.py` | Create | Pilot snapshot centering test |
| `tests/test_text_size.py` | Create | cycling, wrap, persistence, invalid-fallback |
| `docs/engineering/{engine,tui-screens,progress}.md`, `docs/reference/progress-schema.md`, `CHANGELOG.md` | Modify | per AGENTS.md mapping + `[Unreleased]` |

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit (engine) | advances-on-error, backspace-erases, credited accuracy/net_wpm, stars ladder, correction credit | TDD red→green; rewrite `test_engine.py` |
| Unit (progress) | v1→v2 migration, idempotency, round-trip, any-attemptable, completion-unlock, settings fallback | `tmp_path` JSON fixtures |
| Integration (practice) | cascade error→acc→stars→record→unlock; size cycling+persist | `Pilot` `app.run_test()` |
| Visual (centering) | title/stats/text/keyboard centered; regression on revert | Pilot snapshot baseline |

**Engine test rewrite map** — invert: `test_wrong_key_does_not_advance` → advances+records; `test_backspace_does_not_erase_recorded_errors` → erases `error_positions`, keeps `key_errors`. Rewrite: `test_accuracy_with_mixed_correct_and_wrong_attempts` and `test_stars_ladder_boundaries_driven_by_accuracy` for the credited formula (construct sessions with exact first_try/corrected/uncorrected counts). Add: correction-yields-0.5, backspace-over-first-try, net_wpm-credited (5+1 corrected/1min=1.1), typing-past-errors-reaches-completion, never-corrected-yields-0, all-first-try=100%, one-corrected-4-char=87.5%, one-uncorrected-4-char=75%, key_errors-persist-across-backspace. Keep: correct-advances, completion_and_stars, gross_wpm, stars_zero_when_incomplete, backspace_at_zero_is_noop, backspace_after_correct_requires_retyping, newline_matches, metrics_zero_before_first_keystroke, extra_key_after_completion_ignored.

## Migration / Rollout

v1→v2 forward-only, idempotent, on load. v1 file is COPY→`.bak` before first v2 write (never treated as corrupt). Truly corrupt (unparseable / wrong-type / unknown future version) → existing `.bak` rename + fresh v2. No feature flag. Rollback = revert the atomic commit per slice (proposal rollback plan). Engine slice: revert `engine.py` + `test_engine.py` (progress data unaffected; scoring is runtime-only, only bests persist).

## Implementation Order

1. **centered-layout** — CSS only, no domain/tests. (lowest risk)
2. **free-lesson-navigation** — schema v2 + migrator + `settings` block + `is_unlocked`/`is_completion_unlocked`. (text-size depends on this landing `settings`)
3. **text-size-control** — consumes `settings.size`; CSS classes + reactive + bindings.
4. **forgiving-error-model** — engine rewrite + test_engine.py rewrite + `_refresh_text` cascade. (highest risk, last)

De-risking the engine rewrite: (a) write the new `test_engine.py` suite first (red); (b) rewrite `engine.py` to green; (c) add an integration test in `test_practice_flow.py` pinning the full cascade error→accuracy→stars→record→unlock; (d) document the scoring semantic shift in `docs/engineering/engine.md`. Engine commit is atomic and revertible.

## Open Questions

- [ ] Mid-session `accuracy` uses `len(target)` denominator (literal spec) → live ACC climbs from 0% after the first correct char. Confirm with spec author this is desired, or switch to `_position` (attempted-so-far) for the live display only. Affects display, not completed-session values.
- [ ] Textual `text-style: bold` on a `Static` rendering `rich.Text` spans (practice-text) — does it bold span-styled runs, or only plain text? Verify in Pilot snapshot for `size-l`.
- [ ] Exact Textual key name for `+`/`-` (`plus`/`minus` vs literal char) against Textual >=0.60 — verify the binding fires in tasks.
