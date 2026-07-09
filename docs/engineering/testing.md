# Testing

tactile has **76 passing tests** across 7 files, built with strict TDD. This
page explains how to run them, what they cover, and how to add a new test —
especially a Textual `Pilot` test for a screen.

## Running the tests

```sh
uv run pytest -q                    # whole suite: "76 passed"
uv run pytest -q -x                 # stop on the first failure
uv run pytest tests/test_engine.py -q            # one module
uv run pytest tests/test_practice_flow.py -q     # the Pilot tests
uv run pytest -k "stars" -q                       # by name pattern
```

Config is in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

`asyncio_mode = "auto"` means every `async def test_...` is an asyncio test
with no decorator. See [project/pytest.md](../project/pytest.md).

## What the 7 test files cover

| File | Tests* | Covers |
|------|--------|--------|
| `test_engine.py` | 13 | Cursor advance/lock, error recording, WPM/accuracy math, the parametrized star ladder at 90/95/97/99, backspace (no-op at 0, requires retyping, does not erase errors), newline handling, zero-metrics-before-first-key, extra-key-after-completion ignored |
| `test_layouts.py` | 13 | Both layout ids, layout names, en_us `f` is left-index on home row, en_us home-row positions, es_la home row is `asdfghjklñ`, en_us `{` is shift, es_la `@` is AltGr, es_la accented vowels are dead, every `key_order` char is typable (parametrized), no char repeats across entries (parametrized), uppercase resolves to shift, `typable` accepts space/newline and rejects unknown |
| `test_curriculum.py` | 12 | Determinism, first en_us unit only uses `fj` + space, unit count = lessons + reviews + speedtest, WPM ramp 10→40 monotone, all exercise chars typable, review every 5th lesson, no leading/trailing/double spaces, exercise lengths 40-120, speed test is last with one long exercise, es_la reviews include ñ words, wordlist lowercased, es wordlist has accents/ñ |
| `test_progress.py` | 9 | Fresh defaults, set_active_layout persists, record round-trip, best-keeping + key-error accumulation, unlock logic (0 unlocked, 1 needs ≥2 stars), corrupt file → `.bak` + fresh, `best_wpm_for` unseen/after-record, `record_key_errors` accumulates without lessons, no leftover `.tmp` |
| `test_codeload.py` | 12 | utf-8 no notice, latin-1 fallback notice, tabs expanded + indent dropped + trailing stripped, blank lines skipped, 8 lines → 1 exercise, 25 lines → 3 exercises, >2000 lines truncated, untypable removed with notice, untypable kept when layout supports them, CLI `practice` boots into code practice, completing code practice records no lesson, `p` opens the file picker |
| `test_app.py` | 3 | First run shows layout select then map, second run with active layout goes straight to map, fresh store unlocks only the first lesson |
| `test_practice_flow.py` | 4 | Type through unit 1 earns stars + shows results, enter on results returns to a refreshed map with the next unit unlocked, wrong key does not advance, escape returns to map without recording |

\*Function counts; parametrization expands them to 76 total cases.

## The strict-TDD red-green-refactor workflow

Every change to the pure-logic modules followed this loop, and it is the
expected workflow for new work:

1. **Red** — write the failing test first. Run it and confirm it fails for
   the *right* reason (module missing, wrong return value, etc.), not for a
   typo or an import error.
2. **Green** — implement the minimum code to make the test pass. Do not add
   behaviour the test does not demand.
3. **Refactor** — clean up names, extract helpers, remove duplication, with
   the tests still green.

For the UI, the same discipline applied: the `Pilot` test was written
before the screen behaviour. This is why the suite covers both happy paths
and edge cases (wrong key does not advance; escape records nothing; corrupt
progress is backed up; the speed test is the last unit).

## Writing a Pilot test for a new screen

Textual's `Pilot` runs the app headlessly. The pattern, from `test_app.py`:

```python
from tactile.app import TactileApp

async def test_first_run_shows_layout_select_then_map(tmp_path):
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        assert app.screen.__class__.__name__ == "LayoutSelectScreen"
        await pilot.press("enter")        # pick the first layout
        await pilot.pause()
        assert app.screen.__class__.__name__ == "LessonMapScreen"
```

Rules and gotchas:

- **Always pass a `tmp_path` progress file** so the test never touches the
  real `~/.tactile/progress.json`.
- **`asyncio_mode = "auto"`** means no `@pytest.mark.asyncio` decorator.
- **`await pilot.pause()`** after a `press` that triggers a screen
  transition, so the app settles before the next assertion.
- **Space is `"space"`, newline is `"enter"`** in `pilot.press(...)`. When
  typing an exercise's text, map `" "` → `"space"` and `"\n"` → `"enter"`:

  ```python
  for ch in unit.exercises[0].text:
      await pilot.press("enter" if ch == "\n" else ("space" if ch == " " else ch))
  ```

- **Assert on `app.screen.__class__.__name__`** (or `isinstance`) for
  navigation, and on `app.store` for persistence effects.
- **`app.current_unit`** is exposed for tests so you can read the unit
  being practiced.

A full happy-path example (type through a unit and land on results) lives
in `tests/test_practice_flow.py::test_type_through_unit_one_earns_stars_and_shows_results`.

## Coverage

No external coverage tool is configured in 0.1.0. The intended coverage is
the module-to-test-file mapping in
[project/pytest.md](../project/pytest.md#coverage-by-module). Adding
`pytest-cov` to the `dev` group is a natural future step.
