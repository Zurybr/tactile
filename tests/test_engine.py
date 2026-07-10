"""Tests for the pure typing engine (forgiving error model).

Wrong keys ADVANCE the cursor (the learner types past mistakes); backspace
ERASES a recorded error so the position can be re-evaluated; corrected
positions earn 0.5 partial credit; never-corrected errors earn 0.0. The
old edclub "hold-cursor" model is gone — this is the only model.
"""

from __future__ import annotations

import pytest

from tactile.engine import TypingSession


def make(
    target: str = "fj fj", t: list[float] | None = None
) -> tuple[TypingSession, list[float]]:
    # Note: default `t` is created fresh per call (not a shared mutable
    # default argument) so tests that mutate `t[0]` cannot leak state into
    # other tests that also rely on the default clock.
    if t is None:
        t = [0.0]
    session = TypingSession(target, clock=lambda: t[0])
    return session, t


# --- KEPT: behavior unchanged by the forgiving model ------------------------


def test_correct_key_advances():
    s, _ = make("ab")
    assert s.on_key("a") is True
    assert s.position == 1 and s.expected == "b"


def test_completion_and_stars():
    s, t = make("ab")
    s.on_key("a")
    t[0] = 6.0
    s.on_key("b")
    assert s.is_complete
    # 2 chars in 6s -> net_wpm = (2/5)/(0.1min) = 4.0
    assert s.net_wpm == pytest.approx(4.0)
    assert s.accuracy == 100.0
    assert s.stars(wpm_target=4.0) == 5
    assert s.stars(wpm_target=99.0) == 3  # accuracy 100 but wpm target missed -> capped at 3


def test_stars_zero_when_incomplete():
    s, _ = make("ab")
    s.on_key("a")
    assert not s.is_complete
    assert s.stars(wpm_target=1.0) == 0


def test_backspace_at_zero_is_noop():
    s, _ = make("ab")
    s.on_backspace()
    assert s.position == 0
    assert s.expected == "a"


def test_backspace_after_correct_char_requires_retyping_it():
    s, _ = make("ab")
    assert s.on_key("a") is True
    assert s.position == 1
    s.on_backspace()
    assert s.position == 0
    assert s.expected == "a"
    assert s.on_key("a") is True
    assert s.position == 1


def test_newline_matches_enter_char():
    s, _ = make("a\nb")
    s.on_key("a")
    assert s.on_key("\n") is True
    assert s.position == 2
    assert s.expected == "b"


def test_metrics_are_zero_before_first_keystroke():
    s, _ = make("ab")
    assert s.elapsed == 0.0
    assert s.gross_wpm == 0.0
    assert s.net_wpm == 0.0
    assert s.accuracy == 100.0
    assert s.position == 0
    assert s.expected == "a"
    assert s.is_complete is False


def test_extra_key_after_completion_is_ignored():
    s, _ = make("a")
    assert s.on_key("a") is True
    assert s.is_complete
    assert s.on_key("a") is False
    assert s.position == 1
    assert s.error_positions == {}


# --- INVERTED: hold-cursor behavior is now advance-on-error -----------------


def test_wrong_key_advances_and_records_error():
    s, _ = make("ab")
    assert s.on_key("x") is False
    assert s.position == 1  # NEW forgiving model: cursor advances on wrong key
    assert s.error_positions == {0: 1}
    assert s.key_errors == {"a": 1}


def test_backspace_erases_error_position_keeps_key_errors():
    s, _ = make("ab")
    s.on_key("x")  # wrong, recorded at position 0, cursor advances to 1
    s.on_backspace()  # cursor back to 0, error_positions[0] popped
    assert s.position == 0
    assert s.error_positions == {}  # NEW: backspace ERASES the recorded error
    assert s.key_errors == {"a": 1}  # key_errors persists (cumulative heatmap)


# --- REWRITTEN: flows change because cursor advances on wrong keys -----------


def test_gross_wpm_counts_all_keystrokes_including_errors():
    s, t = make("ab")
    s.on_key("x")  # wrong (expected 'a'), advances to position 1
    t[0] = 6.0
    s.on_key("y")  # wrong (expected 'b'), advances to position 2, complete
    assert s.is_complete
    # 2 total keystrokes in 6s -> gross_wpm = (2/5)/(0.1min) = 4.0
    assert s.gross_wpm == pytest.approx(4.0)


def test_accuracy_with_mixed_correct_uncorrected_and_corrected():
    # Target "abcd". Exercises all three position outcomes in one session:
    # - position 0: errored, backspaced, retyped correctly -> corrected (0.5)
    # - position 1: first-try-correct (1.0)
    # - position 2: errored and never revisited -> uncorrected (0.0)
    # - position 3: first-try-correct (1.0)
    s, _ = make("abcd")
    s.on_key("x")  # position 0 wrong (expected 'a'), advances to 1
    s.on_backspace()  # back to position 0, error popped
    s.on_key("a")  # position 0 corrected, advances to 1
    s.on_key("b")  # position 1 first-try, advances to 2
    s.on_key("z")  # position 2 wrong (expected 'c'), advances to 3
    s.on_key("d")  # position 3 first-try, advances to 4, complete
    assert s.is_complete
    # credited = 0.5 + 1.0 + 0.0 + 1.0 = 2.5; total = 4 -> accuracy = 62.5
    assert s.accuracy == pytest.approx(62.5)
    assert s.error_positions == {2: 1}  # only position 2 still errored
    assert s.key_errors == {"a": 1, "c": 1}


@pytest.mark.parametrize(
    ("accuracy_pct", "expected_stars"),
    [
        (100, 5),
        (99, 5),
        (98, 4),
        (97, 4),
        (96, 3),
        (95, 3),
        (94, 2),
        (90, 2),
        (89, 1),
    ],
)
def test_stars_ladder_boundaries_driven_by_accuracy(accuracy_pct: int, expected_stars: int):
    # wpm_target=0.0 makes the wpm gate trivially satisfied, isolating the
    # accuracy thresholds (90/95/97/99) of the star ladder.
    # Construct a 100-char target: type (100 - accuracy_pct) wrongs first
    # (each advances the cursor and stays uncorrected at completion), then
    # accuracy_pct corrects. Credited = accuracy_pct; final accuracy = accuracy_pct%.
    n_correct = accuracy_pct
    n_wrong = 100 - accuracy_pct
    s, _ = make("a" * 100, t=[0.0])
    for _ in range(n_wrong):
        s.on_key("x")  # advances; stays uncorrected (never revisited)
    for _ in range(n_correct):
        s.on_key("a")  # first-try-correct
    assert s.is_complete
    assert s.accuracy == pytest.approx(float(accuracy_pct))
    assert s.stars(wpm_target=0.0) == expected_stars


# --- NEW: forgiving-model scenarios from the spec ---------------------------


def test_typing_past_errors_reaches_completion():
    # Spec scenario: typing only wrong keys still reaches completion.
    s, _ = make("hi")
    s.on_key("x")  # wrong at 0 (expected 'h'), advances
    s.on_key("y")  # wrong at 1 (expected 'i'), advances -> complete
    assert s.position == 2
    assert s.is_complete
    assert s.error_positions == {0: 1, 1: 1}
    assert s.key_errors == {"h": 1, "i": 1}


def test_correction_yields_half_credit():
    # Spec scenario: error -> backspace -> correct yields 0.5 weight (not 1.0).
    s, _ = make("ab")
    s.on_key("x")  # wrong at 0
    s.on_backspace()  # back to 0, error popped
    assert s.on_key("a") is True  # corrected (was ever-errored)
    s.on_key("b")  # first-try, complete
    assert s.is_complete
    # credited = 0.5 + 1.0 = 1.5; total = 2 -> accuracy = 75.0
    assert s.accuracy == pytest.approx(75.0)


def test_backspace_over_first_try_stays_first_try():
    # Spec scenario: backspacing over a position that was never errored
    # leaves no error entry; the position is still first-try on retype.
    s, _ = make("ab")
    s.on_key("a")  # first-try at 0, advances to 1
    s.on_backspace()  # back to 0
    assert s.error_positions == {}
    s.on_key("a")  # re-type; position 0 was never errored -> still first-try
    s.on_key("b")  # complete
    assert s.is_complete
    assert s.accuracy == 100.0  # all first-try


def test_accuracy_all_first_try_is_100():
    # Spec scenario: a perfect run is 100%.
    s, _ = make("cat")
    for ch in "cat":
        s.on_key(ch)
    assert s.is_complete
    assert s.accuracy == 100.0


def test_accuracy_one_corrected_four_char_is_87_5():
    # Spec scenario: "abcd" with position 0 errored + corrected; 1-3 first-try.
    # credited = 0.5 + 1 + 1 + 1 = 3.5; total = 4 -> accuracy = 87.5
    s, _ = make("abcd")
    s.on_key("x")  # position 0 wrong
    s.on_backspace()  # back to 0, error popped
    s.on_key("a")  # corrected
    s.on_key("b")
    s.on_key("c")
    s.on_key("d")
    assert s.is_complete
    assert s.accuracy == pytest.approx(87.5)


def test_accuracy_one_uncorrected_four_char_is_75():
    # Spec scenario: "abcd" with position 0 wrong and never corrected; 1-3 first-try.
    # credited = 0 + 1 + 1 + 1 = 3.0; total = 4 -> accuracy = 75.0
    s, _ = make("abcd")
    s.on_key("x")  # position 0 wrong, advances
    s.on_key("b")  # position 1 first-try
    s.on_key("c")  # position 2 first-try
    s.on_key("d")  # position 3 first-try, complete
    assert s.is_complete
    assert s.accuracy == pytest.approx(75.0)


def test_live_accuracy_uses_attempted_so_far():
    # Spec scenario: live accuracy divides by attempted-so-far, NOT len(target).
    # Session on "abcdef" (6 chars), 3 typed perfectly, NOT complete.
    # Live accuracy = 3.0 / max(3, 1) * 100 = 100.0 (NOT 3.0 / 6 * 100 = 50.0).
    s, _ = make("abcdef")
    s.on_key("a")
    s.on_key("b")
    s.on_key("c")
    assert s.position == 3
    assert not s.is_complete
    assert s.accuracy == pytest.approx(100.0)


def test_final_accuracy_uses_len_target():
    # Spec scenario: once complete, accuracy divides by the full target length.
    # Same session completed perfectly -> 6.0 / 6 * 100 = 100.0.
    s, _ = make("abcdef")
    for ch in "abcdef":
        s.on_key(ch)
    assert s.is_complete
    assert s.accuracy == pytest.approx(100.0)


def test_net_wpm_uses_credited_chars():
    # Spec scenario: 5 first-try-correct + 1 corrected (0.5) over 1 minute
    # -> net_wpm = (5.5 / 5) / 1 = 1.1
    s, t = make("abcdef")
    for ch in "abcde":  # positions 0-4 first-try-correct
        s.on_key(ch)
    s.on_key("x")  # position 5 wrong (expected 'f'), advances, complete
    s.on_backspace()  # back to 5, error popped (position 5 still ever-errored)
    t[0] = 60.0  # 1 minute elapsed since start_time was set to 0.0
    s.on_key("f")  # position 5 corrected, complete
    assert s.is_complete
    assert s.net_wpm == pytest.approx(1.1)


def test_key_errors_persist_across_backspace():
    # key_errors is the cumulative heatmap; backspace never erases it.
    s, _ = make("ab")
    s.on_key("x")  # wrong (expected 'a')
    s.on_backspace()  # pops error_positions[0]
    assert s.error_positions == {}
    assert s.key_errors == {"a": 1}  # heatmap persists


def test_never_corrected_yields_zero_credit():
    # Spec scenario: an error never revisited contributes 0 credit.
    # "abc": position 0 wrong and never revisited; 1-2 first-try.
    # credited = 0 + 1 + 1 = 2.0; total = 3 -> accuracy = 66.66...%
    s, _ = make("abc")
    s.on_key("x")  # position 0 wrong, advances
    s.on_key("b")  # position 1 first-try
    s.on_key("c")  # position 2 first-try, complete
    assert s.is_complete
    assert s.accuracy == pytest.approx(200.0 / 3.0)
