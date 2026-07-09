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
from dataclasses import dataclass
from typing import Literal

from touchtype.layouts import Layout

_VOWELS = set("aeiouáéíóúü")
_WORDLIST_FILES = {"en_us": "en.txt", "es_la": "es.txt"}

_REVIEW_EXERCISE_COUNT = 4
_REVIEW_TARGET_LEN = 80
_SPEEDTEST_TARGET_LEN = 200
_LESSON_DRILL_TARGET_LEN = 60
_LESSON_WORDS_TARGET_LEN = 60
_LESSON_STREAM_TARGET_LEN = 100
_LONG_STREAM_LETTER_THRESHOLD = 12


@dataclass(frozen=True)
class Exercise:
    text: str


@dataclass(frozen=True)
class Unit:
    id: str
    title: str
    kind: Literal["lesson", "review", "speedtest"]
    new_chars: str
    wpm_target: float
    exercises: tuple[Exercise, ...]


def load_wordlist(layout_id: str) -> list[str]:
    filename = _WORDLIST_FILES[layout_id]
    package_files = importlib.resources.files("touchtype.wordlists")
    text = package_files.joinpath(filename).read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def build_curriculum(layout: Layout, words: list[str]) -> list[Unit]:
    typable_words = [w for w in words if w and all(layout.typable(c) for c in w)]

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
                wpm_target=_wpm_target(index, total),
                exercises=exercises,
            )
        )
    return units


def _wpm_target(index: int, total: int) -> float:
    if total <= 1:
        return 10.0
    return round(10.0 + (40.0 - 10.0) * index / (total - 1), 1)


def _build_lesson_exercises(
    layout: Layout,
    new_chars: str,
    pool: frozenset[str],
    words: list[str],
    layout_id: str,
    unit_index: int,
) -> tuple[Exercise, ...]:
    texts: list[str] = []

    rng0 = random.Random(f"{layout_id}:{unit_index}:0")
    texts.append(_drill_tokens(rng0, new_chars, _LESSON_DRILL_TARGET_LEN))

    rng1 = random.Random(f"{layout_id}:{unit_index}:1")
    texts.append(_drill_mixed(rng1, new_chars, pool, _LESSON_DRILL_TARGET_LEN))

    rng2 = random.Random(f"{layout_id}:{unit_index}:2")
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
        rng3 = random.Random(f"{layout_id}:{unit_index}:3")
        texts.append(_word_exercise(rng3, pool, words, _LESSON_STREAM_TARGET_LEN))

    return tuple(Exercise(text=_finalize(t, layout)) for t in texts)


def _build_review_exercises(
    layout: Layout, pool: frozenset[str], words: list[str], layout_id: str, unit_index: int
) -> tuple[Exercise, ...]:
    texts: list[str] = []
    for exercise_index in range(_REVIEW_EXERCISE_COUNT):
        rng = random.Random(f"{layout_id}:{unit_index}:{exercise_index}")
        texts.append(_word_exercise(rng, pool, words, _REVIEW_TARGET_LEN))
    return tuple(Exercise(text=_finalize(t, layout)) for t in texts)


def _build_speedtest_exercise(
    layout: Layout, pool: frozenset[str], words: list[str], layout_id: str, unit_index: int
) -> tuple[Exercise, ...]:
    rng = random.Random(f"{layout_id}:{unit_index}:0")
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


def _finalize(text: str, layout: Layout) -> str:
    filtered = "".join(c for c in text if c == " " or layout.typable(c) and c != "\n")
    return " ".join(filtered.split())
