# Curriculum

`curriculum.py` turns a `Layout`'s `key_order` into a deterministic sequence
of `Unit`s. It is pure logic — no Textual, no filesystem beyond reading
bundled wordlists via `importlib.resources`.

The curriculum has **two tracks**:

- the **spine** — the key-introduction lessons, reviews, and final speed
  test (the original 26–27 units per layout); and
- the **fluency track** — a post-speedtest collection of bigram, common-word,
  sentence, paragraph, number, symbol, code, and speed-burst units that
  drills real-world typing patterns.

## The data model

```python
@dataclass(frozen=True)
class Exercise:
    text: str

@dataclass(frozen=True)
class Unit:
    id: str                                # "en_us-01", "es_la-review-05", "en_us-speedtest", "en_us-fluency-01"
    title: str
    kind: Literal[                         # spine: lesson|review|speedtest
        "lesson", "review", "speedtest",   # fluency:
        "ngram", "common_words",           #   ngram | common_words
        "sentence", "paragraph",           #   sentence | paragraph
        "number", "symbol",                #   number | symbol
        "code", "burst",                   #   code | burst
    ]
    new_chars: str                         # chars this lesson introduces (spine only)
    wpm_target: float                      # spine ramps 10.0 -> 40.0; fluency 40.0 -> 65.0
    exercises: tuple[Exercise, ...]
    track: Literal["spine", "fluency"] = "spine"
```

Both are frozen dataclasses, so a built curriculum is immutable and safely
cacheable on `TactileApp`. The `track` field lets UI/ramp logic branch
cleanly between the spine and the fluency track.

## `build_curriculum(layout, words)`

The build has two stages:

1. **Spine** (`_build_spine`) — walks `layout.key_order` in order and emits,
   for each entry, one `lesson` unit. After every 5th lesson it inserts a
   `review` unit, and after the last lesson it appends a single `speedtest`.

   ```python
   for title, new_chars in layout.key_order:
       pool |= set(new_chars)
       lesson_number += 1
       specs.append(("lesson", title, new_chars, frozenset(pool), lesson_number))
       if lesson_number % 5 == 0:
           specs.append(("review", f"Review: units 1-{lesson_number}", "", frozenset(pool), lesson_number))
   specs.append(("speedtest", "Speed Test", "", frozenset(pool), lesson_number))
   ```

2. **Fluency track** (`build_fluency_track(layout, words, spine_len)`) —
   appended **after** the spine speedtest. It returns the fluency units in
   pedagogical order: ngrams → common words → sentences → paragraphs →
   numbers → symbols → code → bursts. The spine is untouched.

The spine `pool` is the cumulative set of characters learned so far — each
spine lesson and review only uses characters the learner has already been
introduced to. Fluency units assume the full layout is learned.

### Unit counts

| Layout | Spine lessons | Spine reviews | Spine speedtest | **Spine** | Fluency units | **Total** |
|--------|---------------|---------------|-----------------|-----------|---------------|-----------|
| en_us  | 21            | 4             | 1               | **26**    | 37            | **63**    |
| es_la  | 22            | 4             | 1               | **27**    | 33            | **60**    |

The fluency track adds **70 new units** (37 en_us + 33 es_la) and **254 new
exercises** across both layouts. es_la has fewer fluency units because the
**code** group (4 units) is en_us-only — the es_la layout cannot type the
backslash used in several code snippets.

Fluency unit counts per kind:

| Kind          | en_us | es_la | Notes |
|---------------|-------|-------|-------|
| ngram         | 6     | 6     | bigrams + trigrams |
| common_words  | 6     | 6     | three frequency tiers × two units |
| sentence      | 8     | 8     | 8 themed pools of 8 sentences |
| paragraph     | 5     | 5     | themes: typing, nature, tech, daily life, growth |
| number        | 3     | 3     | digits, dates/years, decimals/large |
| symbol        | 3     | 3     | basic, brackets, operators (per-layout typable filter) |
| code          | 4     | —     | en_us only (Python, JS, mixed) |
| burst         | 2     | 2     | short high-speed words + phrases |
| **total**     | **37**| **33**| |

### WPM target ramp

WPM is a **two-segment** monotonic ramp, computed independently per track:

```python
def _wpm_ramp(index, total, lo, hi):
    if total <= 1:
        return lo
    return round(lo + (hi - lo) * index / (total - 1), 1)
```

- **Spine**: `_wpm_ramp(index, spine_total, 10.0, 40.0)` — first lesson 10.0,
  speedtest 40.0.
- **Fluency**: `_wpm_ramp(index, fluency_total, 40.0, 65.0)` — first fluency
  unit 40.0, last fluency unit 65.0.

The overall ramp across the whole unit list is monotonic non-decreasing
(40.0 at the speedtest is followed by 40.0 at the first fluency unit).

## Determinism

All randomness flows through seeded RNGs:

```python
def _rng(layout_id, unit_index, exercise_index):
    return _seeded_rng(layout_id, unit_index, exercise_index)

def _seeded_rng(seed_tag, unit_index, exercise_index):
    return random.Random(f"{seed_tag}:{unit_index}:{exercise_index}")
```

The spine seeds under the layout id; the fluency track seeds under its own
`"{layout_id}:fluency"` namespace, so **fluency content is independent of
how many spine units precede it**. A given `(layout, wordlist)` pair always
produces the exact same curriculum. This is why curricula do not need to be
persisted — rebuilding yields the same units. `test_curriculum.py` pins this
with determinism tests for both tracks.

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

Every exercise text is finalized so every character satisfies
`layout.typable()`. The function has three modes:

```python
def _finalize(text, layout, *, multiline=False, keep_indent=False):
    ...
```

- **Default** (single-line; lessons, reviews, ngrams, common words,
  sentences, numbers, symbols, bursts): drop newlines, collapse whitespace,
  no leading/trailing/double spaces.
- **`multiline=True`** (paragraphs): keep `\n` line breaks, collapse runs of
  spaces within each line, strip each line.
- **`multiline=True, keep_indent=True`** (code): keep `\n` AND leading
  indentation, only rstrip each line (so Python 4-space indents survive).

The lesson "no newline / no double space" test only asserts on
`kind == "lesson"`, so the multi-line fluency kinds are unaffected.

## Review and speed test

- **Review** — 4 word-stream exercises, each ~80 chars, over the full
  learned pool. No new chars.
- **Speed test** — 1 exercise, ~200 chars of words over the full pool. It
  is the **last spine unit** and caps the spine's WPM ramp at 40.0.

## Fluency track

`build_fluency_track(layout, words, spine_len)` produces the post-speedtest
units. It assembles an ordered plan of `(kind, title, builder)` entries and
assigns each a `fluency-{NN}` id, the 40→65 WPM ramp, and `track="fluency"`.
Every builder draws randomness from `_seeded_rng("{layout_id}:fluency", i, j)`.

| Group | Kind | Per-layout | Builder |
|-------|------|-----------|---------|
| Bigrams & trigrams | `ngram` | 6 | `_drill_repeats` over curated EN/ES n-gram lists |
| Common words tiers | `common_words` | 6 | `_sample_exercises` over top-frequency tiers (curated list + bundled wordlist for tier III) |
| Sentences | `sentence` | 8 | join 1–3 sentences from a themed 8-sentence pool |
| Paragraphs | `paragraph` | 5 | pick one original multi-line paragraph (5 themes × 5 paragraphs) |
| Numbers | `number` | 3 | digits; dates & years; decimals & large numbers |
| Symbols | `symbol` | 3 | basic; brackets; operators — filtered to per-layout typable chars |
| Code | `code` | 4 (en_us) | Python imports/defs, Python classes, JavaScript, mixed — `keep_indent` finalize |
| Speed bursts | `burst` | 2 | 6 short (≤60 char) exercises: high-frequency words and short phrases |

### Content provenance

All fluency prose is **original or traditional/public-domain** (proverbs).
No copyrighted text is bundled. Curated frequency lists (common words,
n-grams) are derived from public-domain frequency data. Code snippets are
short, original patterns written for typing practice.

### Length bounds

Every fluency exercise is between 20 and 250 characters
(`_FLUENCY_MIN_LEN` / `_FLUENCY_MAX_LEN`), enforced by a test across both
layouts and all kinds. Paragraphs (3–5 lines) and code (multi-line, indented)
use the multiline finalize path; all other kinds are single-line.

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
