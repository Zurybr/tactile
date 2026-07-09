"""Tests for the curriculum generator and bundled wordlists."""

from __future__ import annotations

from tactile.curriculum import build_curriculum, load_wordlist
from tactile.layouts import LAYOUTS

_SAMPLE_WORDS = [
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
    "cat", "dog", "run", "sun", "big", "red", "top", "fun", "job", "kit",
]


def test_build_curriculum_is_deterministic():
    layout = LAYOUTS["en_us"]
    first = build_curriculum(layout, _SAMPLE_WORDS)
    second = build_curriculum(layout, _SAMPLE_WORDS)
    assert first == second


def test_first_en_us_unit_only_uses_fj_and_space():
    layout = LAYOUTS["en_us"]
    units = build_curriculum(layout, _SAMPLE_WORDS)
    first_unit = units[0]
    assert first_unit.exercises
    for exercise in first_unit.exercises:
        assert set(exercise.text) <= set("fj ")


def test_unit_count_matches_lessons_plus_reviews_plus_speedtest():
    layout = LAYOUTS["en_us"]
    units = build_curriculum(layout, _SAMPLE_WORDS)
    lesson_count = len(layout.key_order)
    review_count = lesson_count // 5
    assert len(units) == lesson_count + review_count + 1


def test_wpm_targets_ramp_from_10_to_40_monotonically():
    layout = LAYOUTS["en_us"]
    units = build_curriculum(layout, _SAMPLE_WORDS)
    targets = [u.wpm_target for u in units]
    assert targets[0] == 10.0
    assert targets[-1] == 40.0
    assert all(b >= a for a, b in zip(targets, targets[1:]))


def test_all_exercise_chars_are_typable():
    layout = LAYOUTS["en_us"]
    units = build_curriculum(layout, _SAMPLE_WORDS)
    for unit in units:
        for exercise in unit.exercises:
            for char in exercise.text:
                assert layout.typable(char), f"{unit.id}: {char!r} not typable"


def test_review_unit_appears_after_every_5th_lesson():
    layout = LAYOUTS["en_us"]
    units = build_curriculum(layout, _SAMPLE_WORDS)
    # First 5 lessons occupy indices 0-4; the review should land at index 5.
    assert units[5].kind == "review"
    lesson_units = [u for u in units if u.kind == "lesson"]
    review_units = [u for u in units if u.kind == "review"]
    assert len(review_units) == len(lesson_units) // 5


def test_lesson_exercises_have_no_leading_trailing_or_double_spaces():
    layout = LAYOUTS["en_us"]
    units = build_curriculum(layout, _SAMPLE_WORDS)
    for unit in units:
        if unit.kind != "lesson":
            continue
        for exercise in unit.exercises:
            text = exercise.text
            assert text == text.strip()
            assert "  " not in text
            assert "\n" not in text


def test_lesson_exercise_lengths_are_within_40_to_120_chars():
    layout = LAYOUTS["en_us"]
    units = build_curriculum(layout, _SAMPLE_WORDS)
    for unit in units:
        if unit.kind != "lesson":
            continue
        for exercise in unit.exercises:
            assert 40 <= len(exercise.text) <= 120, (unit.id, exercise.text)


def test_speedtest_is_last_unit_and_has_one_long_exercise():
    layout = LAYOUTS["en_us"]
    units = build_curriculum(layout, _SAMPLE_WORDS)
    last = units[-1]
    assert last.kind == "speedtest"
    assert len(last.exercises) == 1
    assert len(last.exercises[0].text) >= 150


def test_es_la_review_units_eventually_include_words_with_ene():
    layout = LAYOUTS["es_la"]
    words = load_wordlist("es_la")
    units = build_curriculum(layout, words)
    review_units = [u for u in units if u.kind == "review"]
    assert review_units, "expected at least one review unit"
    all_review_text = " ".join(
        exercise.text for unit in review_units for exercise in unit.exercises
    )
    assert "ñ" in all_review_text


def test_load_wordlist_returns_lowercase_words_for_both_layouts():
    for layout_id in ("en_us", "es_la"):
        words = load_wordlist(layout_id)
        assert len(words) >= 250
        assert all(w == w.lower() for w in words)
        assert all(w.strip() == w for w in words)


def test_load_wordlist_es_has_accented_and_ene_words():
    words = load_wordlist("es_la")
    assert any("ñ" in w for w in words)
    assert any(c in w for w in words for c in "áéíóú")
