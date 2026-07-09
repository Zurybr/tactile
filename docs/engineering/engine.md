# Engine

`engine.py` is the pure typing domain. It has **no I/O and no Textual
dependency** — only `time` and `collections.abc.Callable`. It is fully
unit-testable without an event loop.

## `TypingSession`

```python
class TypingSession:
    def __init__(self, target: str, clock: Callable[[], float] = time.monotonic): ...
    def on_key(self, char: str) -> bool      # True if char matched and cursor advanced
    def on_backspace(self) -> None           # step back one position if position > 0
    position: int                            # index of the next expected char
    expected: str | None                     # target[position], or None when complete
    is_complete: bool                        # position >= len(target)
    elapsed: float                           # seconds since first keystroke; 0.0 before it
    gross_wpm: float                         # (total keystrokes / 5) / minutes
    net_wpm: float                           # (position / 5) / minutes
    accuracy: float                          # correct / total keystrokes * 100 (100.0 if none)
    error_positions: dict[int, int]          # target index -> wrong attempt count
    key_errors: dict[str, int]               # expected char -> wrong attempt count
    def stars(self, wpm_target: float) -> int
```

The clock is **injected** so tests control time: pass a fake `clock` callable
returning controlled floats. The timer starts on the first `on_key` or
`on_backspace` event; `elapsed` is `0.0` before that, so WPM is `0.0` until
the first keystroke.

## The edclub cursor model

The defining rule, matching edclub/TypingClub behaviour:

> **The cursor does NOT advance on a wrong key. Every wrong attempt counts
> against accuracy.**

```python
def on_key(self, char: str) -> bool:
    if self.is_complete:
        return False
    self._mark_first_keystroke()
    expected = self._target[self._position]
    self._total_keystrokes += 1
    if char == expected:
        self._correct_keystrokes += 1
        self._position += 1
        return True
    self._error_positions[self._position] = ...   # count at this index
    self._key_errors[expected] = ...              # count for this expected char
    return False
```

Consequences:

- A wrong key leaves `position` unchanged — the learner must type the right
  one to move on.
- `error_positions` records *where* in the target mistakes happened
  (target index → wrong attempt count).
- `key_errors` records *which expected char* was missed (expected char →
  wrong attempt count). This feeds the worst-keys heatmap in results and
  the per-key error accumulation in the progress store.

### Backspace

`on_backspace()` decrements `position` if it is greater than 0. It does
**not** erase recorded errors or keystrokes — accuracy and the error maps
keep their history. At position 0 it is a no-op.

### Newlines

`on_key("\n")` matches a `\n` in the target. The practice screen maps the
`enter` key to `session.on_key("\n")`, so multi-line targets (including
code-practice exercises) work.

## WPM and accuracy

| Metric | Formula |
|--------|---------|
| `gross_wpm` | `(total_keystrokes / 5) / minutes` |
| `net_wpm` | `(position / 5) / minutes` |
| `accuracy` | `correct_keystrokes / total_keystrokes * 100` (100.0 if no keystrokes) |

`minutes = elapsed / 60`. Both WPM values return `0.0` when `elapsed <= 0`
(guards the division). Net WPM uses `position` (correctly typed chars), so
wrong attempts that did not advance the cursor do not inflate speed. This
is the metric the star rating uses.

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
`_STAR_ACCURACY_THRESHOLDS = (90.0, 95.0, 97.0, 99.0)`. A run with 100%
accuracy but below the WPM target is capped at 3 stars — that is why net
WPM gates only the 4- and 5-star rungs.

### Unit-level aggregation

A unit has multiple exercises. `PracticeScreen` aggregates the per-exercise
results into the unit score:

- **stars** = `min(stars across exercises)` (your worst exercise sets the
  unit rating),
- **accuracy** = mean of per-exercise accuracies,
- **wpm** = mean of per-exercise net WPM,
- **worst keys** = top 3 expected chars by accumulated error count.

The progress store keeps the **best** stars/WPM/accuracy across replays.

## Why the engine is pure

Keeping the cursor model, the metrics, and the star ladder out of Textual
means:

- Tests run synchronously, fast, with an injected clock — no async, no
  terminal.
- The same engine could back a non-TUI front end without changes.
- The WPM/accuracy/star behaviour is pinned by `test_engine.py` (13 tests,
  including the parametrized boundary ladder) before any UI exists.
