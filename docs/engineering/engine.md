# Engine

`engine.py` is the pure typing domain. It has **no I/O and no Textual
dependency** — only `time` and `collections.abc.Callable`. It is fully
unit-testable without an event loop.

## `TypingSession`

```python
class TypingSession:
    def __init__(self, target: str, clock: Callable[[], float] = time.monotonic): ...
    def on_key(self, char: str) -> bool      # True if char matched; False on wrong key (which still advances) or after completion
    def on_backspace(self) -> None           # step back one position if position > 0; pops any error recorded there
    position: int                            # index of the next expected char
    expected: str | None                     # target[position], or None when complete
    is_complete: bool                        # position >= len(target)
    elapsed: float                           # seconds since first on_key; 0.0 before it
    gross_wpm: float                         # (total keystrokes / 5) / minutes
    net_wpm: float                           # (credited chars / 5) / minutes
    accuracy: float                          # credited / total_positions * 100 (100.0 if no keystrokes)
    error_positions: dict[int, int]          # currently-errored position -> wrong attempt count (popped on backspace)
    key_errors: dict[str, int]               # expected char -> cumulative wrong attempt count (never erased)
    def stars(self, wpm_target: float) -> int
```

The clock is **injected** so tests control time: pass a fake `clock` callable
returning controlled floats. The timer starts on the first `on_key` event;
`on_backspace` no longer starts the timer (only `on_key` does). `elapsed` is
`0.0` before the first keystroke, so WPM is `0.0` until then.

## The forgiving cursor model

The defining rule:

> **A wrong key ADVANCES the cursor. Backspace ERASES a recorded error.
> A corrected position earns 0.5 partial credit.**

This is a single replacement model — there is no hold-cursor code path and
no opt-in toggle. The learner types past mistakes instead of being held on
them; the scoring cascade re-evaluates a position when the cursor steps back
over it and it is retyped.

```python
def on_key(self, char: str) -> bool:
    if self.is_complete:
        return False
    self._mark_first_keystroke()
    expected = self._target[self._position]
    self._total_keystrokes += 1
    if char == expected:
        self._position += 1
        return True
    self._ever_errored.add(self._position)              # persists across backspace
    self._error_positions[p] = ...                       # popped on backspace
    self._key_errors[expected] = ...                     # cumulative heatmap
    self._position += 1                                  # ADVANCES (forgiving)
    return False
```

Three error-tracking structures serve three distinct roles:

- `_error_positions` — *currently-errored* positions and their wrong-attempt
  count. **Popped on backspace** so the position can be re-evaluated when
  retyped. Drives the live "still errored" view and the uncorrected count at
  completion.
- `_key_errors` — *cumulative heatmap* of which expected char was missed.
  **Never erased**, not even by backspace. Feeds the worst-keys display and
  the progress-store accumulation.
- `_ever_errored` — positions that were **ever** errored. **Persists across
  backspace**, so the scoring cascade can distinguish corrected (0.5 credit;
  was errored but no longer in `_error_positions`) from first-try (1.0
  credit; never errored). This is the structural difference from the old
  hold-cursor model.

`_ever_errored` is intentionally a `set[int]`, not a count — only "was this
position ever wrong?" matters for crediting; the per-position wrong count
lives in `_error_positions` and the per-char count in `_key_errors`.

### Backspace

`on_backspace()` decrements `position` if it is greater than 0, AND pops
that position's entry from `_error_positions`. It does NOT touch
`_ever_errored` (so the position still counts as corrected if retyped) or
`_key_errors` (the cumulative heatmap is never erased). At position 0 it is
a no-op. Backspace no longer starts the timer — only `on_key` does.

### Correction vs first-try

A position is classified at query time (in `_position_outcomes`) over
`range(position)`:

- in `_ever_errored` AND in `_error_positions` → **uncorrected** (0.0 credit)
- in `_ever_errored` AND NOT in `_error_positions` → **corrected** (0.5 credit)
- otherwise → **first-try-correct** (1.0 credit)

So backspacing over an errored position and typing the right key moves it
from "uncorrected" to "corrected" — never back to "first-try". A position
backspaced over before any error stays first-try.

### Newlines

`on_key("\n")` matches a `\n` in the target. The practice screen maps the
`enter` key to `session.on_key("\n")`, so multi-line targets (including
code-practice exercises) work.

## Scoring cascade

| Metric | Formula |
|--------|---------|
| `gross_wpm` | `(total_keystrokes / 5) / minutes` — unchanged |
| `net_wpm` | `(credited_chars / 5) / minutes` where `credited = first_try * 1.0 + corrected * 0.5` |
| `accuracy` | `(credited_chars / total_positions) * 100` (100.0 if no keystrokes) |

`minutes = elapsed / 60`. Both WPM values return `0.0` when `elapsed <= 0`
(guards the division). Net WPM uses **credited chars**, not `position`:
since a wrong key now advances the cursor, `position` no longer equals the
correct count. This is the metric the star rating uses.

### Live vs final accuracy denominator

`accuracy` has two denominators, selected by completion state:

- **Live** (`is_complete is False`): `total_positions = max(position, 1)` —
  reflects only the characters attempted so far, so a perfect prefix shows
  100% rather than being diluted by the untyped suffix.
- **Final** (`is_complete is True`): `total_positions = len(target)` — the
  full exercise length, so completed runs are scored against the whole.

An empty/untouched session (no keystrokes) returns `100.0`.

Worked examples on a 4-char target `"abcd"`:

| Run | first-try | corrected | uncorrected | credited | accuracy |
|-----|-----------|-----------|-------------|----------|----------|
| all first-try | 4 | 0 | 0 | 4.0 | 100.0 |
| one corrected (pos 0 errored + backspace + retype) | 3 | 1 | 0 | 3.5 | 87.5 |
| one uncorrected (pos 0 errored, never revisited) | 3 | 0 | 1 | 3.0 | 75.0 |

## Star rating

`stars(wpm_target)` returns 0 while incomplete, otherwise a monotone ladder
on accuracy (with a WPM gate at the top two rungs):

| Stars | Condition |
|-------|-----------|
| 0 | not `is_complete` |
| 1 | complete |
| 2 | accuracy >= 90.0 |
| 3 | accuracy >= 95.0 |
| 4 | accuracy >= 97.0 **and** `net_wpm >= wpm_target` |
| 5 | accuracy >= 99.0 **and** `net_wpm >= wpm_target` |

The thresholds are the module constant
`_STAR_ACCURACY_THRESHOLDS = (90.0, 95.0, 97.0, 99.0)` — **unchanged** from
the old model. What changed is the accuracy and net_wpm that feed the
ladder: they now use credited chars. A run with 100% accuracy but below the
WPM target is capped at 3 stars — that is why net WPM gates only the 4- and
5-star rungs. The cascade `error -> _ever_errored -> accuracy -> net_wpm ->
stars` is internally consistent: the same `accuracy`/`net_wpm` feed both
stars and the recorded bests.

### Unit-level aggregation

A unit has multiple exercises. `PracticeScreen` aggregates the per-exercise
results into the unit score:

- **stars** = `min(stars across exercises)` (your worst exercise sets the
  unit rating),
- **accuracy** = mean of per-exercise accuracies,
- **wpm** = mean of per-exercise net WPM,
- **worst keys** = top 3 expected chars by accumulated error count.

The progress store keeps the **best** stars/WPM/accuracy across replays
(max-preservation contract unchanged; only the formulas that produce those
values changed).

## Why the engine is pure

Keeping the cursor model, the metrics, and the star ladder out of Textual
means:

- Tests run synchronously, fast, with an injected clock — no async, no
  terminal.
- The same engine could back a non-TUI front end without changes.
- The WPM/accuracy/star behaviour is pinned by `test_engine.py` (32 tests,
  including the parametrized boundary ladder and the spec's exact-credit
  scenarios) before any UI change touches it.
