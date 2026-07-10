"""Deterministic, layout-aware curriculum generator.

Pure logic module - no Textual dependency. `build_curriculum` turns a
`Layout`'s `key_order` into a sequence of lesson/review/speedtest `Unit`s
with generated practice text. All randomness is seeded by
`f"{layout.id}:{unit_index}:{exercise_index}"` so a given (layout, words)
pair always produces the exact same curriculum.
"""

from __future__ import annotations

import importlib.resources
import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from tactile.layouts import Layout

_VOWELS = set("aeiouáéíóúü")
_WORDLIST_FILES = {"en_us": "en.txt", "es_la": "es.txt"}

_REVIEW_EXERCISE_COUNT = 4
_REVIEW_TARGET_LEN = 80
_SPEEDTEST_TARGET_LEN = 200
_LESSON_DRILL_TARGET_LEN = 60
_LESSON_WORDS_TARGET_LEN = 60
_LESSON_STREAM_TARGET_LEN = 100
_LONG_STREAM_LETTER_THRESHOLD = 12

# Two-segment WPM ramp: the key-introduction spine climbs 10 -> 40 (the
# speedtest is the last spine unit), then the fluency track continues
# 40 -> 65. The overall ramp is monotonic non-decreasing.
_WPM_SPINE_MIN = 10.0
_WPM_SPINE_MAX = 40.0
_WPM_FLUENCY_MIN = 40.0
_WPM_FLUENCY_MAX = 65.0

# Fluency exercise length bounds (docs/engineering/curriculum.md).
_FLUENCY_MIN_LEN = 20
_FLUENCY_MAX_LEN = 250


def _rng(layout_id: str, unit_index: int, exercise_index: int) -> random.Random:
    """The single source of the documented seed format for all curriculum randomness."""
    return _seeded_rng(layout_id, unit_index, exercise_index)


def _seeded_rng(seed_tag: str, unit_index: int, exercise_index: int) -> random.Random:
    """Seeded RNG parametrized by an arbitrary tag (spine uses layout id;
    the fluency track uses ``"{layout_id}:fluency"`` so its content is
    independent of how many spine units precede it)."""
    return random.Random(f"{seed_tag}:{unit_index}:{exercise_index}")


@dataclass(frozen=True)
class Exercise:
    text: str


# A fluency unit reuses one of these kinds. The spine keeps its three legacy
# kinds ("lesson", "review", "speedtest"); every fluency unit sets
# ``track="fluency"`` so UI/ramp logic can branch cleanly.
_FluencyKind = Literal[
    "ngram", "common_words", "sentence", "paragraph",
    "number", "symbol", "code", "burst",
]


@dataclass(frozen=True)
class Unit:
    id: str
    title: str
    kind: Literal["lesson", "review", "speedtest"] | _FluencyKind
    new_chars: str
    wpm_target: float
    exercises: tuple[Exercise, ...]
    track: Literal["spine", "fluency"] = "spine"


def load_wordlist(layout_id: str) -> list[str]:
    filename = _WORDLIST_FILES[layout_id]
    package_files = importlib.resources.files("tactile.wordlists")
    text = package_files.joinpath(filename).read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def build_curriculum(layout: Layout, words: list[str]) -> list[Unit]:
    typable_words = [w for w in words if w and all(layout.typable(c) for c in w)]
    spine_units = _build_spine(layout, typable_words)
    fluency_units = build_fluency_track(layout, typable_words, spine_len=len(spine_units))
    return spine_units + fluency_units


def _build_spine(layout: Layout, typable_words: list[str]) -> list[Unit]:
    """The key-introduction spine: lessons, reviews, and the final speedtest."""
    # (kind, title, new_chars, pool, lesson_number_so_far)
    specs: list[tuple[str, str, str, frozenset[str], int]] = []
    pool: set[str] = set()
    lesson_number = 0
    for title, new_chars in layout.key_order:
        pool |= set(new_chars)
        lesson_number += 1
        specs.append(("lesson", title, new_chars, frozenset(pool), lesson_number))
        if lesson_number % 5 == 0:
            specs.append(
                ("review", f"Review: units 1-{lesson_number}", "", frozenset(pool), lesson_number)
            )
    specs.append(("speedtest", "Speed Test", "", frozenset(pool), lesson_number))

    total = len(specs)
    units: list[Unit] = []
    for index, (kind, title, new_chars, unit_pool, unit_lesson_number) in enumerate(specs):
        if kind == "lesson":
            unit_id = f"{layout.id}-{unit_lesson_number:02d}"
            exercises = _build_lesson_exercises(
                layout, new_chars, unit_pool, typable_words, layout.id, index
            )
        elif kind == "review":
            unit_id = f"{layout.id}-review-{unit_lesson_number:02d}"
            exercises = _build_review_exercises(layout, unit_pool, typable_words, layout.id, index)
        else:
            unit_id = f"{layout.id}-speedtest"
            exercises = _build_speedtest_exercise(layout, unit_pool, typable_words, layout.id, index)

        units.append(
            Unit(
                id=unit_id,
                title=title,
                kind=kind,  # type: ignore[arg-type]
                new_chars=new_chars,
                wpm_target=_wpm_ramp(index, total, _WPM_SPINE_MIN, _WPM_SPINE_MAX),
                exercises=exercises,
                track="spine",
            )
        )
    return units


def _wpm_ramp(index: int, total: int, lo: float, hi: float) -> float:
    """Linear ramp from ``lo`` to ``hi`` across ``total`` positions, 1-decimal."""
    if total <= 1:
        return lo
    return round(lo + (hi - lo) * index / (total - 1), 1)


def _build_lesson_exercises(
    layout: Layout,
    new_chars: str,
    pool: frozenset[str],
    words: list[str],
    layout_id: str,
    unit_index: int,
) -> tuple[Exercise, ...]:
    texts: list[str] = []

    rng0 = _rng(layout_id, unit_index, 0)
    texts.append(_drill_tokens(rng0, new_chars, _LESSON_DRILL_TARGET_LEN))

    rng1 = _rng(layout_id, unit_index, 1)
    texts.append(_drill_mixed(rng1, new_chars, pool, _LESSON_DRILL_TARGET_LEN))

    rng2 = _rng(layout_id, unit_index, 2)
    is_capitals = new_chars.isupper()
    is_symbol_only = bool(new_chars) and not any(c.isalpha() for c in new_chars)
    if is_capitals:
        texts.append(_capitalized_word_exercise(rng2, pool, words, _LESSON_WORDS_TARGET_LEN))
    elif is_symbol_only:
        texts.append(
            _interleaved_tokens(rng2, new_chars, pool, words, _LESSON_WORDS_TARGET_LEN)
        )
    else:
        texts.append(_word_exercise(rng2, pool, words, _LESSON_WORDS_TARGET_LEN))

    distinct_letters = {c for c in pool if c.isalpha()}
    if len(distinct_letters) >= _LONG_STREAM_LETTER_THRESHOLD:
        rng3 = _rng(layout_id, unit_index, 3)
        texts.append(_word_exercise(rng3, pool, words, _LESSON_STREAM_TARGET_LEN))

    return tuple(Exercise(text=_finalize(t, layout)) for t in texts)


def _build_review_exercises(
    layout: Layout, pool: frozenset[str], words: list[str], layout_id: str, unit_index: int
) -> tuple[Exercise, ...]:
    texts: list[str] = []
    for exercise_index in range(_REVIEW_EXERCISE_COUNT):
        rng = _rng(layout_id, unit_index, exercise_index)
        texts.append(_word_exercise(rng, pool, words, _REVIEW_TARGET_LEN))
    return tuple(Exercise(text=_finalize(t, layout)) for t in texts)


def _build_speedtest_exercise(
    layout: Layout, pool: frozenset[str], words: list[str], layout_id: str, unit_index: int
) -> tuple[Exercise, ...]:
    rng = _rng(layout_id, unit_index, 0)
    text = _word_exercise(rng, pool, words, _SPEEDTEST_TARGET_LEN)
    return (Exercise(text=_finalize(text, layout)),)


def _drill_tokens(rng: random.Random, chars: str, target_len: int, token_count: int = 12) -> str:
    source = chars or " "
    tokens = []
    for _ in range(token_count):
        length = rng.randint(2, 4)
        tokens.append("".join(rng.choice(source) for _ in range(length)))
    text = " ".join(tokens)
    while len(text) < target_len:
        length = rng.randint(2, 4)
        text += " " + "".join(rng.choice(source) for _ in range(length))
    return text


def _drill_mixed(
    rng: random.Random, new_chars: str, pool: frozenset[str], target_len: int
) -> str:
    rest = "".join(sorted(pool - set(new_chars))) or new_chars or " "
    new_source = new_chars or rest
    tokens = []
    length = 0
    while length < target_len:
        token_len = rng.randint(2, 4)
        token = "".join(
            rng.choice(new_source) if rng.random() < 0.6 else rng.choice(rest)
            for _ in range(token_len)
        )
        tokens.append(token)
        length += len(token) + 1
    return " ".join(tokens)


def _matching_words(pool: frozenset[str], words: list[str]) -> list[str]:
    return [w for w in words if all(c in pool for c in w)]


def _pseudo_word(rng: random.Random, pool: frozenset[str]) -> str:
    letters = sorted(c for c in pool if c.isalpha()) or sorted(pool) or ["a"]
    vowels = [c for c in letters if c in _VOWELS]
    consonants = [c for c in letters if c not in _VOWELS]
    length = rng.randint(3, 5)
    if vowels and consonants:
        result = []
        use_vowel = rng.choice([True, False])
        for _ in range(length):
            result.append(rng.choice(vowels if use_vowel else consonants))
            use_vowel = not use_vowel
        return "".join(result)
    return "".join(rng.choice(letters) for _ in range(length))


def _word_exercise(
    rng: random.Random, pool: frozenset[str], words: list[str], target_len: int
) -> str:
    matches = _matching_words(pool, words)
    use_real_words = len(matches) >= 5
    tokens: list[str] = []
    length = 0
    while length < target_len:
        word = rng.choice(matches) if use_real_words else _pseudo_word(rng, pool)
        tokens.append(word)
        length += len(word) + 1
    return " ".join(tokens)


def _capitalized_word_exercise(
    rng: random.Random, pool: frozenset[str], words: list[str], target_len: int
) -> str:
    text = _word_exercise(rng, pool, words, target_len)
    return " ".join(w[:1].upper() + w[1:] for w in text.split(" ") if w)


def _interleaved_tokens(
    rng: random.Random,
    new_chars: str,
    pool: frozenset[str],
    words: list[str],
    target_len: int,
) -> str:
    matches = _matching_words(pool, words)
    use_real_words = len(matches) >= 5
    new_chars_list = list(new_chars) or [" "]
    tokens: list[str] = []
    length = 0
    while length < target_len:
        if rng.random() < 0.5:
            token = rng.choice(matches) if use_real_words else _pseudo_word(rng, pool)
        else:
            token = rng.choice(new_chars_list)
        tokens.append(token)
        length += len(token) + 1
    return " ".join(tokens)


def _finalize(
    text: str, layout: Layout, *, multiline: bool = False, keep_indent: bool = False
) -> str:
    """Strip untypable chars and normalize whitespace.

    - Default (single-line, used by lessons/reviews/ngrams/words/...): drop
      newlines, collapse whitespace, no leading/trailing spaces.
    - ``multiline=True`` (paragraphs): keep ``\\n`` line breaks, collapse runs
      of spaces within each line, strip each line.
    - ``multiline=True, keep_indent=True`` (code): keep ``\\n`` AND leading
      indentation, only rstrip each line (so Python ``    `` indents survive).
    """
    if multiline:
        lines = []
        for raw_line in text.split("\n"):
            filtered = "".join(c for c in raw_line if c == " " or layout.typable(c))
            lines.append(filtered.rstrip() if keep_indent else " ".join(filtered.split()))
        return "\n".join(lines).strip("\n")
    filtered = "".join(c for c in text if c == " " or (layout.typable(c) and c != "\n"))
    return " ".join(filtered.split())


# ===========================================================================
# Fluency track (appended after the spine speedtest)
# ===========================================================================
#
# The fluency track is a second collection of units that drills real-world
# typing patterns: n-grams, common words, sentences, paragraphs, numbers,
# symbols, code, and speed bursts. It is appended AFTER the existing speedtest
# so the key-introduction spine and its tests are untouched. Its WPM ramp runs
# 40 -> 65 (the spine already covered 10 -> 40), keeping the overall ramp
# monotonic.
#
# Each unit is produced by a small builder closure that turns
# ``(layout, layout_id, unit_index)`` into a tuple of exercises. All randomness
# flows through the seeded ``_rng`` so the whole track is deterministic and
# rebuilds byte-identically.

# A plan entry: (kind, title, builder). The builder receives the layout, the
# layout id, and the unit's global index (spine_len + fluency position) so its
# ``_rng`` seeds stay unique and stable across rebuilds.
_FluencyBuilder = Callable[[Layout, str, int], tuple[Exercise, ...]]
_FluencyEntry = tuple[_FluencyKind, str, _FluencyBuilder]


def build_fluency_track(
    layout: Layout, words: list[str], spine_len: int
) -> list[Unit]:
    """Build the post-speedtest fluency track for a layout.

    ``spine_len`` is accepted to match the documented signature; the fluency
    content itself is independent of it because fluency units seed their RNG
    under the ``"{layout_id}:fluency"`` namespace rather than offsetting from
    the spine length.
    """
    del spine_len  # content is spine-independent by design
    plan = _fluency_plan(layout, words)
    total = len(plan)
    units: list[Unit] = []
    for i, (kind, title, builder) in enumerate(plan):
        # ``i`` is the fluency position; builders namespace the seed themselves.
        units.append(
            Unit(
                id=f"{layout.id}-fluency-{i + 1:02d}",
                title=title,
                kind=kind,
                new_chars="",
                wpm_target=_wpm_ramp(i, total, _WPM_FLUENCY_MIN, _WPM_FLUENCY_MAX),
                exercises=builder(layout, layout.id, i),
                track="fluency",
            )
        )
    return units


def _fluency_plan(layout: Layout, words: list[str]) -> list[_FluencyEntry]:
    """Ordered fluency plan for a layout. Append new types here in pedagogical order."""
    plan: list[_FluencyEntry] = []
    plan.extend(_ngram_plan(layout))
    return plan


# ---- shared fluency helpers ------------------------------------------------

# Fluency RNGs live in their own seed namespace so the track's content does
# not depend on how many spine units precede it.
_FLUENCY_SEED_TAG = "{layout_id}:fluency"


def _drill_repeats(
    layout: Layout,
    layout_id: str,
    unit_index: int,
    tokens_source: list[str],
    exercise_count: int,
    target_len: int,
) -> tuple[Exercise, ...]:
    """Drill a pool of tokens by repeating them (space-separated) to ``target_len``."""
    seed_tag = _FLUENCY_SEED_TAG.format(layout_id=layout_id)
    texts: list[str] = []
    pool = tokens_source or [" "]
    for ex_i in range(exercise_count):
        rng = _seeded_rng(seed_tag, unit_index, ex_i)
        tokens: list[str] = []
        length = 0
        while length < target_len:
            token = rng.choice(pool)
            tokens.append(token)
            length += len(token) + 1
        texts.append(" ".join(tokens))
    return tuple(Exercise(text=_finalize(t, layout)) for t in texts)


def _sample_exercises(
    layout: Layout,
    layout_id: str,
    unit_index: int,
    pool: list[str],
    exercise_count: int,
    target_len: int,
    *,
    multiline: bool = False,
    keep_indent: bool = False,
    joiner: Callable[[list[str]], str] = lambda toks: " ".join(toks),
) -> tuple[Exercise, ...]:
    """Build ``exercise_count`` exercises by sampling ``target_len`` chars of tokens."""
    seed_tag = _FLUENCY_SEED_TAG.format(layout_id=layout_id)
    texts: list[str] = []
    src = pool or [" "]
    for ex_i in range(exercise_count):
        rng = _seeded_rng(seed_tag, unit_index, ex_i)
        tokens: list[str] = []
        length = 0
        while length < target_len:
            token = rng.choice(src)
            tokens.append(token)
            length += len(token) + 1
        texts.append(joiner(tokens))
    return tuple(
        Exercise(text=_finalize(t, layout, multiline=multiline, keep_indent=keep_indent))
        for t in texts
    )


# ---- 1. Bigrams / Trigrams -------------------------------------------------

_NGRAM_EXERCISE_COUNT = 3
_NGRAM_TARGET_LEN = 40

_BIGRAMS_EN = ["th", "he", "in", "er", "an", "re", "nd", "at", "on", "nt", "ha", "es", "st"]
_TRIGRAMS_EN = ["the", "ing", "and", "ion", "tio", "ent", "ati", "for", "her"]
_BIGRAMS_ES = ["de", "qu", "el", "la", "en", "er", "ar", "re", "on", "al"]
_TRIGRAMS_ES = ["que", "est", "ado", "ara", "ión", "ent", "ier", "nte"]


def _split_half(items: list[str]) -> tuple[list[str], list[str]]:
    """Split a list into two non-empty halves (second falls back to first)."""
    mid = max(1, len(items) // 2)
    second = items[mid:] or items[:mid]
    return items[:mid], second


def _ngram_plan(layout: Layout) -> list[_FluencyEntry]:
    if layout.id == "es_la":
        bigrams, trigrams = _BIGRAMS_ES, _TRIGRAMS_ES
    else:
        bigrams, trigrams = _BIGRAMS_EN, _TRIGRAMS_EN
    bi_a, bi_b = _split_half(bigrams)
    tri_a, tri_b = _split_half(trigrams)
    groups = [
        ("Bigrams I", bi_a),
        ("Bigrams II", bi_b),
        ("Bigrams review", bigrams),
        ("Trigrams I", tri_a),
        ("Trigrams II", tri_b),
        ("Trigrams review", trigrams),
    ]
    return [
        (
            "ngram",
            title,
            _make_ngram_builder(grams),
        )
        for title, grams in groups
    ]


def _make_ngram_builder(grams: list[str]) -> _FluencyBuilder:
    def builder(layout: Layout, layout_id: str, unit_index: int) -> tuple[Exercise, ...]:
        return _drill_repeats(
            layout,
            layout_id,
            unit_index,
            grams,
            _NGRAM_EXERCISE_COUNT,
            _NGRAM_TARGET_LEN,
        )

    return builder
