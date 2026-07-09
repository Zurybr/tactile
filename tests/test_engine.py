"""Tests for the pure typing engine (edclub-style cursor model)."""

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


def test_correct_key_advances():
    s, _ = make("ab")
    assert s.on_key("a") is True
    assert s.position == 1 and s.expected == "b"


def test_wrong_key_does_not_advance_and_records_error():
    s, _ = make("ab")
    assert s.on_key("x") is False
    assert s.position == 0
    assert s.error_positions == {0: 1}
    assert s.key_errors == {"a": 1}


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


def test_accuracy_with_mixed_correct_and_wrong_attempts():
    s, _ = make("ab")
    s.on_key("x")  # wrong at position 0 (expected "a")
    s.on_key("a")  # correct
    s.on_key("y")  # wrong at position 1 (expected "b")
    s.on_key("y")  # wrong at position 1 again
    s.on_key("b")  # correct, complete
    assert s.is_complete
    # 2 correct + 3 wrong = 5 total keystrokes -> accuracy = 2/5 * 100 = 40.0
    assert s.accuracy == pytest.approx(40.0)
    assert s.error_positions == {0: 1, 1: 2}
    assert s.key_errors == {"a": 1, "b": 2}


def test_gross_wpm_counts_all_keystrokes_including_errors():
    s, t = make("ab")
    s.on_key("x")  # wrong
    s.on_key("a")  # correct
    t[0] = 6.0
    s.on_key("b")  # correct, complete
    # 3 total keystrokes in 6s -> gross_wpm = (3/5)/(0.1min) = 6.0
    assert s.gross_wpm == pytest.approx(6.0)


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
    n_correct = accuracy_pct
    n_wrong = 100 - accuracy_pct
    s, _ = make("a" * n_correct, t=[0.0])
    for _ in range(n_wrong):
        s.on_key("x")
    for _ in range(n_correct):
        s.on_key("a")
    assert s.is_complete
    assert s.accuracy == pytest.approx(float(accuracy_pct))
    assert s.stars(wpm_target=0.0) == expected_stars


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


def test_backspace_does_not_erase_recorded_errors():
    s, _ = make("ab")
    s.on_key("x")  # wrong, recorded
    s.on_key("a")  # correct, position 1
    s.on_backspace()  # position back to 0
    assert s.error_positions == {0: 1}
    assert s.key_errors == {"a": 1}


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
