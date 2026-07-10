# Exploration: Curriculum Expansion (100+ new lessons)

> Phase: explore · Scope: `curriculum` · Read-only investigation. No code changed.

## Current State

### Data model (`src/tactile/curriculum.py`)

Two frozen dataclasses — immutable, cacheable on `TactileApp`:

```python
@dataclass(frozen=True)
class Exercise:
    text: str                              # the only field — just the string to type

@dataclass(frozen=True)
class Unit:
    id: str                                # "en_us-01", "es_la-review-05", "en_us-speedtest"
    title: str
    kind: Literal["lesson", "review", "speedtest"]   # ← only 3 kinds exist today
    new_chars: str                         # chars this lesson introduces
    wpm_target: float                      # linear ramp 10.0 → 40.0
    exercises: tuple[Exercise, ...]
```

There is **no concept of "exercise type"** at the Exercise level — an Exercise is just a string. Type differentiation happens at the Unit `kind` level, and inside `_build_lesson_exercises` via fixed positional slots (drill / mixed-drill / word / long-stream).

### How the curriculum is built — `build_curriculum(layout, words)`

Walks `layout.key_order` in order. For each entry: emit one `lesson` unit, growing a cumulative `pool` of learned chars. After every 5th lesson, insert a `review`. After the last lesson, append one `speedtest`. The `pool` is the cumulative set of chars learned so far — every exercise only ever uses already-learned chars.

```python
for title, new_chars in layout.key_order:
    pool |= set(new_chars)
    lesson_number += 1
    specs.append(("lesson", title, new_chars, frozenset(pool), lesson_number))
    if lesson_number % 5 == 0:
        specs.append(("review", f"Review: units 1-{lesson_number}", "", frozenset(pool), lesson_number))
specs.append(("speedtest", "Speed Test", "", frozenset(pool), lesson_number))
```

### Verified unit counts (ran `build_curriculum` against bundled wordlists)

| Layout | Lessons | Reviews (every 5th) | Speedtest | **Total** |
|--------|---------|---------------------|-----------|-----------|
| en_us  | 21      | 4                   | 1         | **26**    |
| es_la  | 22      | 4                   | 1         | **27**    |

es_la has one extra lesson because of the dedicated `("Acentos y diéresis", "áéíóúü")` unit. Per layout, that's 26–27 units today. Two layouts → **~53 units total in the app**.

### Progression model

Home-row-first (F&J → D&K → S&L → A&;), center (G&H), then top row outward, bottom row outward, **Capitals (Shift)**, **Punctuation**, **Numbers**, **Symbols**, **Code symbols I & II**. Each lesson adds 2 chars (or a full symbol set for the late units). This is the standard touch-typing progression — pedagogically sound and should be preserved as the foundation.

### Exercise generation (deterministic, seeded)

All randomness flows through one seed: `_rng(layout_id, unit_index, exercise_index) = random.Random(f"{layout_id}:{unit_index}:{exercise_index}")`. Same `(layout, words)` → byte-identical curriculum every build. This is **why curricula are not persisted** — rebuilding is free and stable.

Each **lesson** builds 3 (or 4) exercises, in fixed order:

| # | Exercise | Target len | When |
|---|----------|-----------|------|
| 1 | Drill on **new chars only** (`fff jjj fjf`) | 60 | always |
| 2 | Drill **mixing new + pool** (~60% new) | 60 | always |
| 3 | **Words** over the pool (capitals→capitalize initials; symbol-only→interleave; else plain) | 60 | always |
| 4 | Longer **word stream** | 100 | only if pool ≥ 12 distinct letters |

**Review** = 4 word-stream exercises (~80 chars each). **Speedtest** = 1 exercise (~200 chars).

Word exercises use **real words** when ≥5 matching words exist in the wordlist; otherwise they fall back to **pseudo-words** (3–5 chars, vowel/consonant alternation). `_finalize()` strips any char the layout can't type, drops newlines, and collapses whitespace.

### Wordlists (`src/tactile/wordlists/`)

| File | Words | Format |
|------|-------|--------|
| `en.txt` | 300 | plain text, one lowercase word per line |
| `es.txt` | 300 | plain text, one lowercase word per line; includes `ñ` and accented vowels |

Loaded via `importlib.resources` (bundled as package data, no network). Filtered per layout by `layout.typable(c)`. **300 words is small** — it forces the pseudo-word fallback for narrow pools and limits variety in word exercises and reviews.

### Layouts (`src/tactile/layouts/`)

Two layouts: `en_us` (QWERTY) and `es_la` (Latin-American Spanish, with dead-key accents `áéíóúü`, AltGr `@`, `¿¡`). `Layout` carries `key_order` (the lesson introduction sequence — the curriculum's spine), `char_map` (what's typable, used by `_finalize` and wordlist filtering), and `typable()` (space + newline always allowed). Adding a new keyboard layout (Dvorak, AZERTY) is a separate concern from adding lessons — it would reuse the same curriculum generator.

### Code/text practice (the only "real prose" path today)

`codeload.load_code_exercises(path, layout)` reads any utf-8/latin-1 file, strips untypable chars, and chunks into 10-line exercises — **preserving newlines**. Reached only via CLI `tactile practice <path>`, **not** as curriculum units, and `record_progress=False`. This proves the engine and practice screen already handle multi-line `\n` text; lesson exercises only avoid `\n` because `_finalize()` drops it.

### Progress coupling (`progress.py`)

`ProgressStore` keys on `(layout_id, unit.id)` and tracks `stars`, `best_wpm`, `best_acc`, and a cumulative `key_errors` heatmap per layout. Unlocking is **free navigation** (every unit always attemptable); a completion badge is a separate `is_completion_unlocked` derived from `stars >= 2`. The heatmap is a **goldmine for adaptive review** — it records which keys the learner misses, but nothing currently consumes it for content selection.

## Locked-in behavior (tests in `tests/test_curriculum.py`)

These tests **constrain** any expansion and would need updating if the rules change:

- `test_unit_count_matches_lessons_plus_reviews_plus_speedtest` — total = `len(key_order) + len(key_order)//5 + 1`
- `test_wpm_targets_ramp_from_10_to_40_monotonically` — first=10.0, last=40.0, monotonic
- `test_first_en_us_unit_only_uses_fj_and_space`
- `test_lesson_exercise_lengths_are_within_40_to_120_chars` — **only checks `kind == "lesson"`**
- `test_lesson_exercises_have_no_leading_trailing_or_double_spaces` — lessons drop `\n`
- `test_speedtest_is_last_unit_and_has_one_long_exercise` — speedtest must be last
- `test_load_wordlist_returns_lowercase_words_for_both_layouts` — ≥250 words, lowercase
- determinism test

Key implication: **adding new unit kinds (sentence/paragraph/code) is safe** for the length/newline tests (they only assert on `kind=="lesson"`), but the unit-count and WPM-ramp tests pin the current formula and would need to evolve.

## Gaps — what is missing

| Gap | Evidence | Impact |
|-----|----------|--------|
| **No sentence practice** | `kind` has no `sentence`; exercises are single-line word streams | Learner never practices capitalization + punctuation in real context |
| **No paragraph / multi-line practice** | `_finalize()` drops `\n` for lessons (only `codeload` keeps it) | No prose fluency path in the curriculum |
| **No n-gram / common-bigram drills** | No generator for `th he in er an re on at en nd` | Misses the highest-frequency motor patterns |
| **No number-heavy / date / sequence drills** | Numbers introduced once, never revisited in context | Weak transfer to real numeric typing |
| **No symbol-in-context drills** | Symbols introduced once; only `_interleaved_tokens` mixes them with words | Code/URL/email-style typing underrepresented |
| **No weak-key review** | `key_errors` heatmap collected but never read for content | No spaced-repetition / adaptive practice |
| **Tiny wordlists (300 words)** | `en.txt`/`es.txt` both 300 lines | Forces pseudo-word fallback; low variety |
| **No common-words / high-frequency tier** | Wordlists are flat, unranked | Can't drill "the 100 most common words" |
| **No mixed-case fluency** beyond one Capitals unit | Only the Capitals unit capitalizes | Sentence-style casing undertrained |
| **No timed/burst mini-drills** | All units are "type the whole text" | No speed-isolation practice |
| **Code practice not in curriculum** | Only via `tactile practice <file>`, `record_progress=False` | Code fluency has no progression/stars |

## Expansion Opportunities

The cleanest mental model: **keep the key-introduction spine (26–27 units) intact as the foundation**, then add new exercise *types* as additional units in a **post-speedtest "fluency track"** (and optionally a parallel per-tier insertion). Each new type = one new generator function + possibly one new `kind`.

### Option A — Extend `key_order` (more granular key lessons)
Add more entries to `KEY_ORDER_EN` / `KEY_ORDER_ES` (e.g. split numbers into "digits 1-5" / "6-0", add numpad patterns). Pros: zero new code paths. Cons: tiny yield (~5–10 units per layout), still all drill-style. **Effort: Low.**

### Option B — New unit kinds with new generators (sentence / paragraph / ngram / code)
Add `sentence`, `paragraph`, `ngram`, `code` to the `kind` Literal and write generator functions, each consuming new bundled data sources (sentences.txt, paragraphs.txt, code snippets). Pros: high pedagogical value, real-prose fluency, the big numbers (50–80 units per layout). Cons: new data files, new generators, must extend the unit-count/WPM tests, `_finalize()` needs a newline-preserving path for paragraphs. **Effort: Medium-High.**

### Option C — Fluency track after the speedtest
Insert a second collection of units after the current speedtest: common-words drills (100/200/500 most-frequent), bigram/trigram drills, sentence packs, paragraph packs, code-snippet packs, timed burst drills. Each is a self-contained unit with its own WPM target. Pros: doesn't disturb the existing spine or its tests; natural "what's next" after graduation; easy to hit 100+ units. Cons: needs the new generators from Option B underneath. **Effort: Medium-High** (mostly content authoring + generators).

### Option D — Adaptive weak-key review (consumes `key_errors`)
A new unit kind whose exercise text is generated from the learner's accumulated error heatmap, drilled against the keys they actually miss. Pros: uniquely personalized, leverages data already collected. Cons: non-deterministic across users (breaks the "curriculum is identical for everyone" property — needs careful design), needs a new generation path. **Effort: High.**

### Option E — Grow wordlists + add frequency tiers
Expand `en.txt`/`es.txt` from 300 → 1000+ words, sourced from public-domain frequency lists (e.g. Google's 10k English, RAE/CREA Spanish). Optionally split into `en-common-100.txt`, `en-common-500.txt`. Pros: immediately improves every existing word exercise and review; no new code. Cons: licensing/quality curation; alone yields 0 new *units* but multiplies variety. **Effort: Low-Medium** (mostly curation).

## Recommendation

**Combine B + C + E to exceed 100 new lessons across both layouts, while preserving the existing spine and determinism.**

Concretely (per layout, ×2 layouts ≈ doubles counts):

1. **Fluency track (Option C)** — appended after the existing speedtest:
   - N-gram drills: ~3 units (bigrams, trigrams, common suffixes `-ing -ed -tion`)
   - Common-words tiers: ~3 units (top-50, top-100, top-300 words)
   - Sentence packs: ~8–10 units (short → long, mixed case + punctuation)
   - Paragraph packs: ~5–6 units (multi-line, real prose)
   - Code-snippet packs: ~5–6 units (Python/JS-style lines, symbols in context)
   - Number/sequence drills: ~2 units (dates, phone-style, arithmetic)
   - Timed burst drills: ~3 units (short high-speed bursts)
   - **≈ 30–35 new units per layout → ~60–70 across both layouts**

2. **Extend `key_order` (Option A)** for finer-grained late units (split symbols, add a couple of numpad/review-style entries) → **~4–6 extra lesson units per layout → ~10 across both**.

3. **Grow wordlists (Option E)** from 300 → 1000+ words, with frequency tiers — multiplies variety inside all the above without adding unit counts, and feeds the common-words tiers.

4. **Defer Option D** (adaptive weak-key review) to a follow-up change — it's high-value but needs its own design pass around determinism vs. personalization.

**Total realistic yield: 70–90+ new units, comfortably "at least 100" when counting both layouts and the granular key_order additions, with room to tune.**

Pedagogical ordering for the fluency track: ngrams → common words → short sentences → long sentences → paragraphs → code → numbers → bursts. Speed ramp continues past the graduation speedtest's 40 WPM into a higher band (e.g. 40 → 65 WPM across the fluency track).

## Affected Areas

- `src/tactile/curriculum.py` — new generators, new `kind` literals, extended `build_curriculum`, finalize path for multi-line
- `src/tactile/wordlists/` — new data files (sentences, paragraphs, code snippets, ngrams); grow en.txt/es.txt
- `src/tactile/layouts/en_us.py`, `src/tactile/layouts/es_la.py` — optional `key_order` extension
- `src/tactile/progress.py` — no schema change needed; new unit ids just flow through
- `src/tactile/screens/lesson_map.py` — no change (renders any `Unit`); possibly a section header for the fluency track
- `tests/test_curriculum.py` — MUST update unit-count + WPM-ramp tests; add tests for every new generator
- `docs/engineering/curriculum.md` — MUST rewrite unit-count table and document new kinds/data sources
- `docs/index.md` — no change unless new docs added
- `CHANGELOG.md` — `[Unreleased] / Added` entry

## Risks

- **Test churn**: `test_unit_count_matches_lessons_plus_reviews_plus_speedtest` and `test_wpm_targets_ramp_from_10_to_40_monotonically` currently assume the single-spine formula. Adding a fluency track changes both the count and the WPM ceiling. Must be redesigned, not just bumped.
- **Determinism invariant**: every new generator MUST use the seeded `_rng` pattern or the cache-and-rebuild property breaks. Risk is low if convention is followed.
- **`_finalize()` newline stripping**: paragraph units need `\n` preserved. Either branch on `kind` in `_finalize` or use a separate finalizer for multi-line kinds. Must keep the "no `\n` in lessons" test green (it only checks `kind=="lesson"`, so branching is safe).
- **Content licensing/quality**: sentences and paragraphs need a clean source (public domain — e.g. Project Gutenberg for EN; public-domain ES texts). Curation effort is real.
- **Wordlist filter shrinkage**: new content must pass `layout.typable()` per layout — sentences with layout-incompatible chars (e.g. `"` in es_la where it's a shift of `2`) need verification per layout, or they get silently stripped.
- **Scope creep / 400-line PR budget**: 100+ units of content + generators will blow the review budget. Should be delivered as **chained PRs** (one per exercise type: ngrams, then sentences, then paragraphs, …), each with its own tests and doc update. Flag for `sdd-tasks` forecast.
- **Open question for the user**: should new units count toward the existing WPM ramp (10→40) or start a new ramp (40→65) in a separate "fluency" band? Affects star difficulty and the monotonic-ramp test.

## Ready for Proposal

**Yes.** Recommend the orchestrator run **sdd-propose** next, scoped to `curriculum`, to convert Option B+C+E into a concrete change proposal with a rollback plan. The proposal should answer the open question about the WPM ramp band and confirm the chained-PR delivery strategy before spec/design.
