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
    plan.extend(_common_words_plan(layout, words))
    plan.extend(_sentences_plan(layout))
    plan.extend(_paragraphs_plan(layout))
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


# ---- 2. Common words tiers -------------------------------------------------

_COMMON_WORDS_EXERCISE_COUNT = 3
_COMMON_WORDS_TARGET_LEN = 50

# Top-frequency English words (public-domain frequency-list selection).
_COMMON_EN = [
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "it",
    "for", "not", "on", "with", "he", "as", "you", "do", "at", "this",
    "but", "his", "by", "from", "they", "we", "say", "her", "she", "or",
    "an", "will", "my", "one", "all", "would", "there", "their", "what",
    "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
    "when", "make",
    "can", "like", "time", "no", "just", "him", "know", "take", "people",
    "into", "year", "your", "good", "some", "could", "them", "see",
    "other", "than", "then", "now", "look", "only", "come", "its",
    "over", "think", "also", "back", "after", "use", "two", "how",
    "our", "work", "first", "well", "way", "even", "new", "want",
    "because", "any", "these", "give", "day", "most", "us",
]

# Top-frequency Spanish words (public-domain frequency-list selection).
_COMMON_ES = [
    "el", "la", "de", "que", "y", "en", "un", "ser", "con", "por",
    "para", "no", "haber", "poder", "decir", "este", "hacer", "todo",
    "mucho", "también", "saber", "ver", "su", "yo", "venir", "donde",
    "bien", "tiempo", "mismo", "ya", "cosa", "vida", "dar", "mundo",
    "creer", "pues", "ello", "tras", "ojo", "año",
    "encontrarse", "agua", "casa", "seguridad", "sentir", "gran",
    "tipo", "semana", "blanco", "ciudad", "imagen", "dinero", "bailar",
]


def _common_words_plan(layout: Layout, words: list[str]) -> list[_FluencyEntry]:
    base = _COMMON_ES if layout.id == "es_la" else _COMMON_EN
    # Three frequency tiers: top half, full curated list, curated + wordlist.
    tier1 = base[: max(1, len(base) // 2)]
    tier2 = base
    extra = [w for w in words if w not in base]
    tier3 = base + extra
    tiers = [
        ("top words I", tier1),
        ("top words II", tier2),
        ("top words III", tier3),
    ]
    plan: list[_FluencyEntry] = []
    for tier_label, pool in tiers:
        for part in ("a", "b"):
            plan.append(
                (
                    "common_words",
                    f"Common words: {tier_label} ({part})",
                    _make_common_words_builder(pool),
                )
            )
    return plan


def _make_common_words_builder(pool: list[str]) -> _FluencyBuilder:
    def builder(layout: Layout, layout_id: str, unit_index: int) -> tuple[Exercise, ...]:
        return _sample_exercises(
            layout,
            layout_id,
            unit_index,
            pool,
            _COMMON_WORDS_EXERCISE_COUNT,
            _COMMON_WORDS_TARGET_LEN,
        )

    return builder


# ---- 3. Sentences ----------------------------------------------------------

_SENTENCE_EXERCISE_COUNT = 4
_SENTENCE_MIN_LEN = 45  # join 1-3 sentences until this length is reached

# Eight pools of eight sentences each, per language. Content is original or
# traditional/public-domain (proverbs). No copyrighted text.
_SENTENCE_POOLS_EN: list[list[str]] = [
    [  # practice & learning (original)
        "Practice makes perfect when you show up every day.",
        "Small steps taken daily add up to great distances.",
        "The journey of a thousand miles begins with a single step.",
        "Repetition is the mother of all learning.",
        "Patience and steady effort win the race.",
        "A slow start today becomes a fast finish tomorrow.",
        "Focus on accuracy first and speed will follow.",
        "Mistakes are proof that you are trying.",
    ],
    [  # common proverbs (traditional, public domain)
        "The early bird catches the worm.",
        "Actions speak louder than words.",
        "A picture is worth a thousand words.",
        "When in Rome do as the Romans do.",
        "The pen is mightier than the sword.",
        "Better late than never.",
        "Look before you leap.",
        "Every cloud has a silver lining.",
    ],
    [  # time & life (traditional/public domain + original)
        "Time flies when you are having fun.",
        "A stitch in time saves nine.",
        "Time and tide wait for no one.",
        "An apple a day keeps the doctor away.",
        "The grass is always greener on the other side.",
        "Rome was not built in a day.",
        "Knowledge itself is a kind of power.",
        "Two heads are better than one.",
    ],
    [  # nature (original)
        "The river carved its path through the soft stone over many years.",
        "Pine trees stand tall against the winter sky.",
        "The morning sun warmed the quiet valley below.",
        "Birds returned to the lake as the ice melted away.",
        "A gentle breeze carried the scent of rain across the field.",
        "The forest grows quiet when the snow begins to fall.",
        "Waves rolled onto the empty beach at dawn.",
        "Stars slowly appeared above the dark mountain ridge.",
    ],
    [  # technology (original)
        "A good keyboard makes every keystroke feel lighter.",
        "Save your work often to avoid losing progress.",
        "The program ran faster after we cleaned up the code.",
        "He wrote a short script to rename all the files.",
        "Back up your data before you update the system.",
        "The new laptop boots in just a few seconds.",
        "Clear names make code easier to read later.",
        "The team shipped the feature ahead of schedule.",
    ],
    [  # daily life (original)
        "She poured coffee and opened her notebook for the day.",
        "The train arrived just as the rain began to fall.",
        "He packed a light bag and headed for the station.",
        "They met at the corner cafe every Sunday morning.",
        "The garden needed water after the long dry week.",
        "Dinner was simple but warm and filling.",
        "She locked the door and walked into the cool evening.",
        "The children laughed as the kite climbed higher into the sky.",
    ],
    [  # wisdom / sayings (traditional, public domain)
        "Honesty is the best policy in every season of life.",
        "Do not put all your eggs in one basket.",
        "A friend in need is a friend indeed.",
        "The squeaky wheel gets the grease.",
        "You cannot judge a book by its cover.",
        "Necessity is the mother of invention.",
        "Practice what you preach to those around you.",
        "Where there is smoke there is usually fire.",
    ],
    [  # quick thoughts (original)
        "Keep your notes close and your ideas even closer.",
        "A clean desk helps to clear a tired mind.",
        "Drink water and rest your eyes throughout the day.",
        "Read a little every single day without fail.",
        "Kind words cost nothing and mean a great deal.",
        "The best time to start is right about now.",
        "Finish what you begin before you start anew.",
        "Curiosity turns beginners into true experts.",
    ],
]

_SENTENCE_POOLS_ES: list[list[str]] = [
    [  # práctica y aprendizaje (original)
        "La práctica hace al maestro con el tiempo.",
        "Quien no arriesga no gana ninguna partida.",
        "El conocimiento es una forma de poder.",
        "Aprender poco a poco lleva muy lejos.",
        "La constancia vence al talento dormido.",
        "Cada día trae una nueva oportunidad.",
        "Los errores también enseñan lecciones.",
        "La paciencia es la madre de la ciencia.",
    ],
    [  # refranes tradicionales (dominio público)
        "No hay mal que por bien no venga.",
        "Al mal tiempo hay que darle buena cara.",
        "El que mucho abarca poco aprieta.",
        "Más vale tarde que nunca en la vida.",
        "Más vale pájaro en mano que ciento volando.",
        "A buen entendedor pocas palabras bastan.",
        "Más vale prevenir que tener que curar.",
        "En boca cerrada no entran moscas.",
    ],
    [  # sabiduría (tradicional/dominio público + original)
        "Dime con quién andas y te diré quién eres.",
        "El que mucho sabe casi nunca habla demás.",
        "A quien madruga Dios le ayuda en el camino.",
        "No por mucho madrugar amanece más temprano.",
        "Ojos que no ven corazón que no siente.",
        "Quien siembra vientos recoge tempestades.",
        "El hábito no hace al monje que lo lleva.",
        "De la nada al todo hay mucho trecho aún.",
    ],
    [  # naturaleza (original)
        "El río cortó la piedra con los años lentos.",
        "Los pinos se alzaban bajo el cielo de invierno.",
        "El sol de la mañana calentó el valle entero.",
        "Las aves volvieron al lago al derretirse el hielo.",
        "La brisa traía el olor fresco de la lluvia.",
        "El bosque guarda silencio al caer la nieve.",
        "Las olas llegaban a la playa casi vacía.",
        "Las estrellas brillaban sobre la montaña oscura.",
    ],
    [  # tecnología (original)
        "Un buen teclado aligera cada una de las teclas.",
        "Guarda tu trabajo con mucha frecuencia.",
        "El programa corrió más rápido al limpiar el código.",
        "Escribió un script para renombrar los archivos.",
        "Respalda tus datos antes de actualizar el sistema.",
        "La computadora nueva enciende en pocos segundos.",
        "Los nombres claros facilitan leer el código después.",
        "El equipo entregó la función antes del plazo fijado.",
    ],
    [  # vida diaria (original)
        "Sirvió café y abrió su cuaderno del día.",
        "El tren llegó justo al empezar la lluvia.",
        "Empacó una bolsa ligera y fue a la estación.",
        "Se veían los domingos en la cafetería del barrio.",
        "El jardín necesitaba agua tras la semana seca.",
        "La cena fue sencilla pero cálida y buena.",
        "Cerró la puerta y salió al fresco de la noche.",
        "Los niños reían al subir la cometa al cielo.",
    ],
    [  # naturaleza humana / vida (original)
        "La amabilidad no cuesta nada en absoluto.",
        "Las palabras honestas abren muchas puertas.",
        "Un buen hábito puede cambiar toda tu semana.",
        "Caminar un rato despeja la mente cansada.",
        "Leer un poco cada día enriquece el espíritu.",
        "El orden del escritorio aclara las ideas.",
        "Descansar la vista también es una forma de trabajar.",
        "La curiosidad convierte a los novatos en expertos.",
    ],
    [  # pensamientos breves (original)
        "Empieza hoy mismo lo que postergaste ayer.",
        "Termina una cosa antes de empezar otra nueva.",
        "Bebe agua y respira hondo varias veces al día.",
        "Escribe tus ideas antes de que se vuelen.",
        "La práctica diaria construye gran destreza.",
        "Un paso pequeño también es un avance válido.",
        "Escucha con atención antes de responder nada.",
        "La gratitud cambia el ánimo de todo el día.",
    ],
]


def _sentences_plan(layout: Layout) -> list[_FluencyEntry]:
    pools = _SENTENCE_POOLS_ES if layout.id == "es_la" else _SENTENCE_POOLS_EN
    return [
        ("sentence", f"Sentences {i + 1}", _make_sentence_builder(pool))
        for i, pool in enumerate(pools)
    ]


def _make_sentence_builder(pool: list[str]) -> _FluencyBuilder:
    def builder(layout: Layout, layout_id: str, unit_index: int) -> tuple[Exercise, ...]:
        seed_tag = _FLUENCY_SEED_TAG.format(layout_id=layout_id)
        texts: list[str] = []
        for ex_i in range(_SENTENCE_EXERCISE_COUNT):
            rng = _seeded_rng(seed_tag, unit_index, ex_i)
            chosen: list[str] = []
            length = 0
            # join 1-3 sentences until the target length is reached
            while length < _SENTENCE_MIN_LEN and len(chosen) < 3:
                sentence = rng.choice(pool)
                chosen.append(sentence)
                length += len(sentence) + 1
            texts.append(" ".join(chosen))
        return tuple(Exercise(text=_finalize(t, layout)) for t in texts)

    return builder


# ---- 4. Paragraphs ---------------------------------------------------------

_PARAGRAPH_EXERCISE_COUNT = 3
_PARAGRAPH_THEMES = ["Typing", "Nature", "Technology", "Daily life", "Growth"]

# Five themed units, each with five original multi-line paragraphs
# (~3-4 lines, 150-250 chars). No copyrighted text.
_PARAGRAPH_POOLS_EN: list[list[str]] = [
    [  # typing
        "Learning to type well pays you back for your whole life.\n"
        "Every keystroke saved is a small moment returned to you.\n"
        "Start on the home row, let your fingers learn the keys,\n"
        "and soon you will type without looking down at all.",
        "Good posture makes typing easier on your hands and back.\n"
        "Keep your wrists flat and your elbows close to your sides,\n"
        "and your eyes level with the top edge of the screen.\n"
        "Small habits now prevent strain in the years ahead.",
        "Accuracy comes first, and speed follows close behind it.\n"
        "Type each letter with care rather than rushing ahead.\n"
        "When your fingers know the path, they move on their own,\n"
        "and the words appear on the screen almost by magic.",
        "A steady rhythm beats short bursts of frantic typing.\n"
        "Find a calm pace you can hold for many quiet minutes.\n"
        "The keyboard becomes a bridge straight to your thoughts,\n"
        "and ideas flow out as fast as your mind can form them.",
        "Mistakes are part of practice, not a sign of failure.\n"
        "Notice the keys that trip you up and drill them more.\n"
        "Each small session adds a little strength to your hands,\n"
        "and the skill quietly turns into a lifelong habit.",
    ],
    [  # nature
        "The forest wakes slowly in the cool morning air.\n"
        "Mist hangs between the trunks and fades in the light.\n"
        "A single bird calls, and another answers from afar.\n"
        "The day begins its quiet work of growth and renewal.",
        "Rain fills the river and pushes it over its banks.\n"
        "Water carries leaves and small branches to the sea.\n"
        "Nothing is wasted in the long loop of the seasons.\n"
        "Each drop finds its way back to the wide ocean.",
        "High on the ridge the wind never seems to rest.\n"
        "It shapes the short trees into low bending forms.\n"
        "Below, the valley sleeps under a soft blanket of fog.\n"
        "The mountain keeps its silence through the long years.",
        "The desert blooms for a few bright weeks each year.\n"
        "Seeds that waited in the dry earth open at once.\n"
        "Color spills across the sand and then fades away.\n"
        "Life here is brief, fierce, and full of quiet purpose.",
        "Tides pull the water back to reveal a strip of sand.\n"
        "Small crabs hurry across the wet and shining ground.\n"
        "Shells gather where the waves finally come to a stop.\n"
        "The shore breathes in and out with the pull of the moon.",
    ],
    [  # technology
        "A computer is only as useful as the person who guides it.\n"
        "Learn the basic ideas before you chase the newest tools.\n"
        "Clear thinking turns a blank screen into a working program,\n"
        "and patience turns rough code into something you trust.",
        "Back up your work before you change anything at all.\n"
        "A second copy has saved more projects than any clever trick.\n"
        "Keep notes on what you tried and what you learned from it.\n"
        "Good habits today protect the work of many quiet hours.",
        "The best programs are often the simplest ones to read.\n"
        "Choose clear names and split big tasks into smaller steps.\n"
        "Test each piece before you join it to the very next one.\n"
        "Simple code is easier to fix, to change, and to share.",
        "Networks carry our words around the world in a moment.\n"
        "A message leaves your screen and reaches a distant friend.\n"
        "Behind that simple act sit layers of careful design,\n"
        "built by many people over many patient years of work.",
        "Automation takes a dull task and hands it to a machine.\n"
        "What once took hours can finish in a few short seconds.\n"
        "The hard part is naming the steps with real precision,\n"
        "for the machine follows your words as you wrote them.",
    ],
    [  # daily life / travel
        "The train rocks gently as the fields roll slowly past.\n"
        "A hot drink warms your hands against the morning chill.\n"
        "There is time to read, to think, or simply watch the view.\n"
        "Travel turns ordinary hours into a quiet little gift.",
        "Markets open early with piles of fresh and bright fruit.\n"
        "Vendors call out their prices in a friendly rising song.\n"
        "The smell of warm bread drifts out from a corner shop.\n"
        "A slow walk through the stalls is its own kind of joy.",
        "Evenings at home have a simple and restful kind of charm.\n"
        "Dinner simmers on the stove while the table is being set.\n"
        "The day's long list of tasks finally comes to a close.\n"
        "There is real comfort in these quiet and familiar hours.",
        "A long walk clears the dust that gathers in the mind.\n"
        "The same streets look different when you slow your pace.\n"
        "You notice small doors, old signs, and hidden gardens.\n"
        "The city shares its secrets with those who stop to look.",
        "Packing a bag is the first small step of any real journey.\n"
        "You choose what matters and leave the rest far behind you.\n"
        "With less to carry, your hands and your mind feel lighter.\n"
        "Soon a new place will greet you with its own clear light.",
    ],
    [  # growth / habits
        "A new habit starts small and grows with daily practice.\n"
        "Five minutes today beats one hour done once a month.\n"
        "Show up at the same time and the habit takes root in you.\n"
        "Soon the effort fades and the action simply feels natural.",
        "Reading a little each day quietly reshapes how you think.\n"
        "Books carry the distilled work of many thoughtful lives.\n"
        "A few pages in the morning can steady your whole day.\n"
        "Ideas you meet on the page return to help you later on.",
        "Writing things down frees your mind from holding them.\n"
        "A short list turns a vague worry into a clear set of steps.\n"
        "Notes capture thoughts before they slip away from you.\n"
        "Later you can review, refine, and act on what you wrote.",
        "Rest is not the opposite of work but a quiet part of it.\n"
        "Tired hands make more mistakes and far slower decisions.\n"
        "A short break returns your focus and your steady patience.\n"
        "Long progress depends on many small and wise pauses.",
        "Curiosity is the quiet engine behind all real learning.\n"
        "Ask why things work, then ask how they could work better.\n"
        "The best learners keep the open mind of a true beginner.\n"
        "Each question you ask is a small door to a wider world.",
    ],
]

_PARAGRAPH_POOLS_ES: list[list[str]] = [
    [  # mecanografía
        "Aprender a escribir bien te beneficia toda la vida.\n"
        "Cada tecla que ahorras es un momento que recuperas.\n"
        "Comienza con la fila inicial, deja que tus dedos aprendan,\n"
        "y pronto escribirás sin mirar el teclado para nada.",
        "Una buena postura hace que escribir sea más liviano.\n"
        "Mantén las muñecas rectas y los codos cerca del cuerpo,\n"
        "y los ojos a la altura de la parte alta de la pantalla.\n"
        "Los buenos hábitos de hoy cuidan tus manos mañana.",
        "Primero viene la precisión y después llega la velocidad.\n"
        "Escribe cada letra con cuidado en lugar de apurarte.\n"
        "Cuando tus dedos conocen el camino, se mueven solos,\n"
        "y las palabras aparecen en la pantalla casi solas.",
        "Un ritmo estable vence a las ráfagas de pura prisa.\n"
        "Busca un paso tranquilo que puedas sostener un buen rato.\n"
        "El teclado se vuelve un puente hacia tus propias ideas,\n"
        "y escribes casi a la velocidad en que vas pensando.",
        "Los errores son parte de la práctica, no un fracaso.\n"
        "Fíjate en las teclas que te cuestan y repítelas más.\n"
        "Cada sesión corta añade un poco de fuerza a tus manos,\n"
        "y la habilidad se vuelve un hábito para toda la vida.",
    ],
    [  # naturaleza
        "El bosque despierta despacio en el aire fresco del día.\n"
        "La niebla cuelga entre los troncos y se va con la luz.\n"
        "Un solo pájaro canta y otro le responde a lo lejos.\n"
        "El día empieza su trabajo callado de crecer y renovar.",
        "La lluvia llena el río y lo empuja fuera de su cauce.\n"
        "El agua lleva hojas y ramas pequeñas hasta el mar.\n"
        "Nada se pierde en el largo ciclo de las estaciones.\n"
        "Cada gota encuentra el camino de regreso al océano.",
        "Allá arriba en la sierra el viento nunca se aquieta.\n"
        "Da forma a los árboles bajos y los dobla con su fuerza.\n"
        "Abajo, el valle duerme bajo una niebla suave y baja.\n"
        "La montaña guarda su silencio a lo largo de los años.",
        "El desierto florece unas semanas brillantes al año.\n"
        "Las semillas que esperaban en la tierra seca se abren.\n"
        "El color se derrama sobre la arena y luego se apaga.\n"
        "La vida aquí es breve, fuerte y está llena de sentido.",
        "La marea retira el agua y deja una franja de arena.\n"
        "Pequeños cangrejos cruzan el suelo mojado y brillante.\n"
        "Las conchas se juntan donde las olas al fin se detienen.\n"
        "La orilla respira con el tirón silencioso de la luna.",
    ],
    [  # tecnología
        "Una computadora sirve tanto como quien sabe guiarla.\n"
        "Aprende las ideas básicas antes de buscar lo más nuevo.\n"
        "El pensamiento claro convierte la pantalla en un programa,\n"
        "y la paciencia vuelve el código rudo en algo confiable.",
        "Respalda tu trabajo antes de cambiar algo importante.\n"
        "Una copia extra ha salvado más proyectos que un truco.\n"
        "Anota lo que probaste y lo que aprendiste de ello.\n"
        "Los buenos hábitos de hoy protegen muchas horas serenas.",
        "Los mejores programas suelen ser los más fáciles de leer.\n"
        "Elige nombres claros y divide las tareas en pasos cortos,\n"
        "y prueba cada parte antes de unirla con la siguiente.\n"
        "El código simple es más fácil de arreglar y de compartir.",
        "Las redes llevan nuestras palabras por el mundo en un instante.\n"
        "Un mensaje sale de tu pantalla y llega a un amigo lejano.\n"
        "Detrás de ese acto simple hay capas de diseño cuidado,\n"
        "hechas por mucha gente a lo largo de muchos años.",
        "La automatización toma una tarea y la da a la máquina.\n"
        "Lo que tomaba horas puede acabar en unos pocos segundos.\n"
        "La parte difícil es describir los pasos con precisión,\n"
        "pues la máquina sigue tus palabras tal como las escribiste.",
    ],
    [  # vida diaria / viajes
        "El tren se mece suave mientras pasan despacio los campos.\n"
        "Una bebida caliente te calienta las manos en la mañana.\n"
        "Hay tiempo para leer, pensar o solo mirar el paisaje.\n"
        "El viaje vuelve horas comunes en un regalo tranquilo.",
        "Los mercados abren temprano con montones de fruta fresca.\n"
        "Los vendedores gritan sus precios en un canto amable.\n"
        "El olor del pan tibio sale de una tienda en la esquina.\n"
        "Pasear despacio por los puestos es su propia alegría.",
        "Las noches en casa tienen un encanto simple y muy quieto.\n"
        "La cena hierve en la estufa mientras se pone la mesa.\n"
        "La larga lista de tareas del día por fin llega a su fin.\n"
        "Hay un consuelo real en estas horas tranquilas y propias.",
        "Una caminata larga limpia el polvo que junta la mente.\n"
        "Las mismas calles se ven distintas al aflojar el paso.\n"
        "Notas puertas pequeñas, letreros viejos y jardines ocultos.\n"
        "La ciudad comparte secretos con quien se detiene a mirar.",
        "Hacer la maleta es el primer paso de cualquier viaje.\n"
        "Eliges lo que importa y dejas el resto muy atrás.\n"
        "Con menos para cargar, las manos y la mente se aligeran.\n"
        "Pronto un lugar nuevo te recibirá con su propia luz clara.",
    ],
    [  # crecimiento / hábitos
        "Un hábito nuevo empieza pequeño y crece con la práctica.\n"
        "Cinco minutos hoy valen más que una hora al mes.\n"
        "Aparece a la misma hora y el hábito echa raíces en ti.\n"
        "Pronto el esfuerzo se desvanece y la acción se siente natural.",
        "Leer un poco cada día cambia despacio cómo piensas.\n"
        "Los libros llevan el trabajo fino de muchas vidas profundas.\n"
        "Unas páginas por la mañana pueden calmar todo tu día.\n"
        "Las ideas del libro regresan para ayudarte más adelante.",
        "Escribir las cosas libera a la mente de tener que retenerlas.\n"
        "Una lista corta vuelve una vaga inquietud en pasos claros.\n"
        "Las notas atrapan los pensamientos antes de que se escapen.\n"
        "Luego puedes repasar, afinar y actuar sobre lo que escribiste.",
        "El descanso no es lo opuesto al trabajo sino parte callada.\n"
        "Las manos cansadas cometen más errores y deciden más lento.\n"
        "Un descanso corto devuelve el enfoque y la paciencia firme.\n"
        "El avance largo depende de muchas pausas pequeñas y sabias.",
        "La curiosidad es el motor callado de todo aprendizaje real.\n"
        "Pregunta por qué funcionan las cosas y cómo podrían mejorar.\n"
        "Los mejores alumnos guardan la mente abierta del novato.\n"
        "Cada pregunta que haces es una puerta a un mundo más ancho.",
    ],
]


def _paragraphs_plan(layout: Layout) -> list[_FluencyEntry]:
    pools = _PARAGRAPH_POOLS_ES if layout.id == "es_la" else _PARAGRAPH_POOLS_EN
    return [
        (
            "paragraph",
            f"Paragraph: {_PARAGRAPH_THEMES[i]}",
            _make_paragraph_builder(pool),
        )
        for i, pool in enumerate(pools)
    ]


def _make_paragraph_builder(pool: list[str]) -> _FluencyBuilder:
    def builder(layout: Layout, layout_id: str, unit_index: int) -> tuple[Exercise, ...]:
        seed_tag = _FLUENCY_SEED_TAG.format(layout_id=layout_id)
        texts: list[str] = []
        for ex_i in range(_PARAGRAPH_EXERCISE_COUNT):
            rng = _seeded_rng(seed_tag, unit_index, ex_i)
            texts.append(rng.choice(pool))
        return tuple(Exercise(text=_finalize(t, layout, multiline=True)) for t in texts)

    return builder
