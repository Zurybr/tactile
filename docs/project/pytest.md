# pytest

tactile's test suite runs on **pytest** with **pytest-asyncio**. As of 0.1.0
the suite has **76 passing tests** across 7 files, built with strict TDD.

## Configuration

Config lives in `pyproject.toml` (there is no separate `pytest.ini`):

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- **`asyncio_mode = "auto"`** — every `async def test_...` is automatically
  treated as an asyncio test. No `@pytest.mark.asyncio` decorator needed.
  This keeps Textual `Pilot` tests terse.
- **`testpaths = ["tests"]`** — pytest discovers tests only under `tests/`.

Run the suite:

```sh
uv run pytest -q          # quiet: "76 passed"
uv run pytest -q -x       # stop on the first failure
uv run pytest tests/test_engine.py -q   # one module
```

## pytest-asyncio and the Pilot tests

The UI tests drive Textual headlessly with the `Pilot` API. Because
`asyncio_mode = "auto"`, an async test just runs:

```python
async def test_first_run_shows_layout_select_then_map(tmp_path):
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        assert app.screen.__class__.__name__ == "LayoutSelectScreen"
        await pilot.press("enter")      # pick the first layout
        await pilot.pause()
        assert app.screen.__class__.__name__ == "LessonMapScreen"
```

Pilot tests use a throwaway progress file under `tmp_path` so they never
touch the real `~/.tactile/progress.json`. See
[engineering/testing.md](../engineering/testing.md) for how to write a new
Pilot test.

## The strict-TDD approach

Every pure-logic module was built red-green-refactor:

1. **Red** — write the failing test first; run it and confirm it fails for
   the right reason.
2. **Green** — implement the minimum to pass.
3. **Refactor** — clean up with the tests still green.

The UI followed the same discipline with `Pilot` tests written before the
screen behaviour. This is why the suite covers both the happy path and the
edge cases (wrong key does not advance the cursor; escape records nothing;
corrupt progress is backed up; the speed test is the last unit; etc.).

## What the 76 tests cover

| Test file | Functions | Covers |
|-----------|-----------|--------|
| `test_engine.py` | 13 | Cursor model, WPM/accuracy math, star ladder at the 90/95/97/99 boundaries, backspace, newline, completion guards |
| `test_layouts.py` | 13 | Both layout ids, home-row positions, en_us shift braces, es_la AltGr `@`, es_la dead-key vowels, `typable()` rules, no `key_order` char repeats |
| `test_curriculum.py` | 12 | Determinism, unit counts, WPM ramp 10→40, all exercise chars typable, reviews every 5th lesson, speed test placement, es_la ñ words, wordlist contents |
| `test_progress.py` | 9 | Fresh defaults, persistence round-trip, best-keeping, unlock logic, corrupt-file backup, `record_key_errors`, no leftover `.tmp` |
| `test_codeload.py` | 12 | utf-8/latin-1, tab expansion, indentation stripping, blank-line skip, line-count chunking, 2000-line cap, untypable removal, CLI boot, no lesson progress for code |
| `test_app.py` | 3 | First-run layout select, returning-user map, fresh-store unlocks only unit 1 |
| `test_practice_flow.py` | 4 | Type through a unit and earn stars, results return to a refreshed map, wrong key does not advance, escape records nothing |

The 66 test functions expand to 76 cases through parametrization (e.g. the
star-ladder boundary test and the per-layout `key_order` checks).

## Coverage by module

| Module | Test file |
|--------|-----------|
| `engine.py` | `test_engine.py` |
| `layouts/` | `test_layouts.py` |
| `curriculum.py` | `test_curriculum.py` |
| `progress.py` | `test_progress.py` |
| `codeload.py` | `test_codeload.py` |
| `app.py` + `screens/` | `test_app.py`, `test_practice_flow.py`, `test_codeload.py` (Pilot tests) |

No external coverage tool is configured in 0.1.0; the mapping above is the
intended coverage. Adding `pytest-cov` is a natural future step.
