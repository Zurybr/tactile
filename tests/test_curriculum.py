"""Tests for the curriculum generator and bundled wordlists."""

from __future__ import annotations

import pytest

from tactile.curriculum import build_curriculum, build_fluency_track, load_wordlist
from tactile.layouts import LAYOUTS

_SAMPLE_WORDS = [
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
    "cat", "dog", "run", "sun", "big", "red", "top", "fun", "job", "kit",
]

_FLUENCY_KINDS = {
    "ngram", "common_words", "sentence", "paragraph",
    "number", "symbol", "code", "burst",
}


def _spine(units): return [u for u in units if u.track == "spine"]
def _fluency(units): return [u for u in units if u.track == "fluency"]


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
    spine = _spine(units)
    lesson_count = len(layout.key_order)
    review_count = lesson_count // 5
    assert len(spine) == lesson_count + review_count + 1


def test_spine_wpm_targets_ramp_from_10_to_40_monotonically():
    layout = LAYOUTS["en_us"]
    units = build_curriculum(layout, _SAMPLE_WORDS)
    targets = [u.wpm_target for u in _spine(units)]
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
    spine = _spine(units)
    last_spine = spine[-1]
    assert last_spine.kind == "speedtest"
    assert len(last_spine.exercises) == 1
    assert len(last_spine.exercises[0].text) >= 150
    # The fluency track is appended AFTER the spine speedtest.
    assert _fluency(units), "expected a fluency track after the spine speedtest"
    assert units[-1].track == "fluency"


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


# ---------------------------------------------------------------------------
# Fluency track (post-speedtest)
# ---------------------------------------------------------------------------


def test_fluency_wpm_ramps_from_40_to_65_monotonically():
    for layout_id in ("en_us", "es_la"):
        layout = LAYOUTS[layout_id]
        units = build_curriculum(layout, _SAMPLE_WORDS)
        targets = [u.wpm_target for u in _fluency(units)]
        assert targets, f"{layout_id}: expected fluency units"
        assert targets[0] == 40.0
        assert targets[-1] == 65.0
        assert all(b >= a for a, b in zip(targets, targets[1:]))


def test_overall_wpm_ramp_is_monotonic_across_spine_and_fluency():
    for layout_id in ("en_us", "es_la"):
        layout = LAYOUTS[layout_id]
        units = build_curriculum(layout, _SAMPLE_WORDS)
        targets = [u.wpm_target for u in units]
        assert all(b >= a for a, b in zip(targets, targets[1:])), layout_id


def test_fluency_units_have_namespaced_ids_and_track_field():
    for layout_id in ("en_us", "es_la"):
        layout = LAYOUTS[layout_id]
        units = build_curriculum(layout, _SAMPLE_WORDS)
        for u in _fluency(units):
            assert u.track == "fluency"
            assert u.id.startswith(f"{layout_id}-fluency-")
            assert u.kind in _FLUENCY_KINDS


def test_fluency_units_only_use_typable_chars():
    for layout_id in ("en_us", "es_la"):
        layout = LAYOUTS[layout_id]
        units = build_curriculum(layout, _SAMPLE_WORDS)
        for unit in _fluency(units):
            for exercise in unit.exercises:
                assert exercise.text, f"{unit.id}: empty exercise"
                for char in exercise.text:
                    assert layout.typable(char), f"{unit.id}: {char!r} not typable"


def test_build_curriculum_deterministic_with_fluency_track():
    for layout_id in ("en_us", "es_la"):
        layout = LAYOUTS[layout_id]
        first = build_curriculum(layout, _SAMPLE_WORDS)
        second = build_curriculum(layout, _SAMPLE_WORDS)
        assert first == second, layout_id


def test_build_fluency_track_is_deterministic_and_independent_of_caller():
    layout = LAYOUTS["en_us"]
    via_build = _fluency(build_curriculum(layout, _SAMPLE_WORDS))
    direct = build_fluency_track(layout, _SAMPLE_WORDS, spine_len=999)
    # Same seeds => same exercises; ids differ only because spine_len differs,
    # so compare exercises + wpm ordering, not ids.
    assert len(via_build) == len(direct)
    for a, b in zip(via_build, direct):
        assert a.exercises == b.exercises
        assert a.kind == b.kind
        assert a.title == b.title


@pytest.mark.parametrize("layout_id", ["en_us", "es_la"])
def test_ngram_fluency_units_present_and_well_formed(layout_id):
    layout = LAYOUTS[layout_id]
    units = build_curriculum(layout, _SAMPLE_WORDS)
    ngram_units = [u for u in _fluency(units) if u.kind == "ngram"]
    assert len(ngram_units) >= 6, layout_id
    for unit in ngram_units:
        assert 3 <= len(unit.exercises) <= 4, unit.id
        for ex in unit.exercises:
            assert 20 <= len(ex.text) <= 80, (unit.id, ex.text)
            assert "\n" not in ex.text
            assert ex.text == ex.text.strip()
            assert "  " not in ex.text

