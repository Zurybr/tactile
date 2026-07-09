# Curriculum

`curriculum.py` turns a `Layout`'s `key_order` into a deterministic sequence
of `Unit`s. It is pure logic — no Textual, no filesystem beyond reading
bundled wordlists via `importlib.resources`.

## The data model

```python
@dataclass(frozen=True)
class Exercise:
    text: str

@dataclass(frozen=True)
class Unit:
    id: str                                # "en_us-01", "es_la-review-05", "en_us-speedtest"
    title: str
    kind: Literal["lesson", "review", "speedtest"]
    new_chars: str                         # the chars this lesson introduces
    wpm_target: float                      # ramps 10.0 -> 40.0 across the unit list
    exercises: tuple[Exercise, ...]
```

Both are frozen dataclasses, so a built curriculum is immutable and safely
cacheable on `TactileApp`.

## `build_curriculum(layout, words)`

The build walks `layout.key_order` in order and emits, for each entry, one
`lesson` unit. After every 5th lesson it inserts a `review` unit, and after
the last lesson it appends a single `speedtest`.

```python
for title, new_chars in layout.key_order:
    pool |= set(new_chars)
    lesson_number += 1
    specs.append(("lesson", title, new_chars, frozenset(pool), lesson_number))
    if lesson_number % 5 == 0:
        specs.append(("review", f"Review: units 1-{lesson_number}", "", frozenset(pool), lesson_number))
specs.append(("speedtest", "Speed Test", "", frozenset(pool), lesson_number))
```

The `pool` is the cumulative set of characters learned so far — each lesson
and review only uses characters the learner has already been introduced to.

### Unit counts

The number of units depends on how many `key_order` entries a layout has:

| Layout | Lessons | Reviews (every 5th) | Speed test | Total units |
|--------|---------|---------------------|------------|-------------|
| en_us | 21 | 4 (after 5, 10, 15, 20) | 1 | **26** |
| es_la | 22 | 4 (after 5, 10, 15, 20) | 1 | **27** |

es_la has one more lesson because it has a dedicated
`("Acentos y diéresis", "áéíóúü")` unit that en_us does not. (Note: the
project description historically referred to a "22-unit curriculum"; the
actual generated counts are 26 for en_us and 27 for es_la.)

### WPM target ramp

Each unit's `wpm_target` is a linear ramp from 10.0 (first unit) to 40.0
(last unit), rounded to one decimal, computed across the full unit list:

```python
def _wpm_target(index: int, total: int) -> float:
    if total <= 1:
        return 10.0
    ramp = (40.0 - 10.0) * index / (total - 1)
    return round(10.0 + ramp, 1)
```

The targets rise monotonically, so later units demand more speed for the
4- and 5-star rungs (see [engine.md](engine.md#star-rating)).

## Determinism

All randomness flows through a single seeded RNG:

```python
def _rng(layout_id, unit_index, exercise_index):
    return random.Random(f"{layout_id}:{unit_index}:{exercise_index}")
```

A given `(layout, wordlist)` pair always produces the exact same curriculum.
This is why curricula do not need to be persisted — rebuilding yields the
same units. `test_curriculum.py` pins this with a determinism test.

## Lesson exercises

Each lesson unit builds 3-5 exercises, in this order:

| # | Exercise | Target length | When |
|---|----------|---------------|------|
| 1 | Drill on the **new chars** only (`fff jjj fjf jfj`) | 60 | always |
| 2 | Drill **mixing new chars with the learned pool** (~60% new) | 60 | always |
| 3 | **Words** over the learned pool | 60 | always |
| 4 | A longer **word stream** | 100 | only if the pool has >= 12 distinct letters |

Exercise 3 adapts to the lesson type:

- **Capitals** unit (`new_chars` is all uppercase) → capitalize word
  initials.
- **Symbol-only** units (no alphabetic chars, e.g. punctuation/numbers) →
  interleave words with the new tokens (`word (word) [word]`).
- Otherwise → plain word exercise.

Word exercises use **real words** from the bundled wordlist when at least 5
matching words exist (all of a word's chars are in the learned pool).
Otherwise they fall back to **pseudo-words**: 3-5 chars seeded from the
pool, with vowel/consonant alternation when vowels are available.

### `_finalize`

Every exercise text is finalized: characters the layout cannot type are
removed, newlines inside lesson exercises are dropped, and whitespace is
collapsed (no leading/trailing/double spaces). This guarantees every
exercise char satisfies `layout.typable()`.

## Review and speed test

- **Review** — 4 word-stream exercises, each ~80 chars, over the full
  learned pool. No new chars.
- **Speed test** — 1 exercise, ~200 chars of words over the full pool. It
  is always the last unit and has the highest WPM target.

## Wordlists

```python
_WORDLIST_FILES = {"en_us": "en.txt", "es_la": "es.txt"}

def load_wordlist(layout_id: str) -> list[str]:
    package_files = importlib.resources.files("tactile.wordlists")
    text = package_files.joinpath(filename).read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]
```

| File | Words | Notes |
|------|-------|-------|
| `wordlists/en.txt` | 300 | common English words, lowercase |
| `wordlists/es.txt` | 300 | common Spanish words, lowercase, with `ñ` and accented vowels (`año`, `café`, `música`, …) |

Bundled as package data and read via `importlib.resources`, so there is no
network access at build or runtime. Before building, `build_curriculum`
filters the wordlist down to words whose every char the layout can type
(`layout.typable(c)`), so each curriculum only uses words it can render.

## Sequential unlocking

Unlocking is enforced by the `ProgressStore`, not the curriculum — but the
curriculum's stable unit ordering is what makes it work. A unit at index `i`
is unlocked when `stars_for(units[i-1].id) >= 2`; index 0 is always
unlocked. See [progress.md](progress.md#sequential-unlocking).
