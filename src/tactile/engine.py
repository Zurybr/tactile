"""Pure typing session engine.

Implements the forgiving cursor model: a wrong key ADVANCES the cursor (the
learner types past mistakes), backspace ERASES a recorded error so the
position can be re-evaluated when retyped, and scoring awards partial credit
(0.5) for positions errored then later corrected. No I/O, no Textual
dependency - this module is pure domain logic.
"""

from __future__ import annotations

import time
from collections.abc import Callable

_STAR_ACCURACY_THRESHOLDS = (90.0, 95.0, 97.0, 99.0)


class TypingSession:
    """Tracks progress typing a single target string."""

    def __init__(self, target: str, clock: Callable[[], float] = time.monotonic) -> None:
        self._target = target
        self._clock = clock
        self._position = 0
        self._start_time: float | None = None
        self._total_keystrokes = 0
        # Per-position current error count. Popped on backspace so a position
        # can be re-evaluated when the cursor steps back over it and it is
        # retyped. Drives the live "still errored" view and the uncorrected
        # count at completion.
        self._error_positions: dict[int, int] = {}
        # Cumulative heatmap of which expected char was missed. Never erased
        # (not even by backspace) - feeds the worst-keys display and the
        # progress-store accumulation.
        self._key_errors: dict[str, int] = {}
        # Positions that were EVER errored. Persists across backspace so the
        # scoring cascade can distinguish corrected (0.5 credit, was errored
        # but no longer in ``_error_positions``) from first-try (1.0 credit,
        # never errored). This is the structural difference from the old
        # hold-cursor model: the fact that a position was once wrong is
        # remembered even after the error is erased.
        self._ever_errored: set[int] = set()

    @property
    def position(self) -> int:
        return self._position

    @property
    def expected(self) -> str | None:
        if self._position >= len(self._target):
            return None
        return self._target[self._position]

    @property
    def is_complete(self) -> bool:
        return self._position >= len(self._target)

    @property
    def elapsed(self) -> float:
        if self._start_time is None:
            return 0.0
        return self._clock() - self._start_time

    @property
    def gross_wpm(self) -> float:
        return self._wpm(self._total_keystrokes)

    @property
    def net_wpm(self) -> float:
        # Credited chars, not raw position: a wrong key now advances the
        # cursor, so ``position`` no longer equals the correct count.
        return self._wpm(self._credited_chars())

    def _wpm(self, char_count: float) -> float:
        minutes = self.elapsed / 60.0
        if minutes <= 0:
            return 0.0
        return (char_count / 5) / minutes

    @property
    def accuracy(self) -> float:
        if self._total_keystrokes == 0:
            return 100.0
        # Live display divides by attempted-so-far so the readout reflects
        # real performance so far (a perfect prefix shows 100%, not a value
        # diluted by the untyped suffix). Final accuracy divides by the full
        # target length so completed runs are scored against the whole.
        total_positions = len(self._target) if self.is_complete else max(self._position, 1)
        return (self._credited_chars() / total_positions) * 100

    @property
    def error_positions(self) -> dict[int, int]:
        return dict(self._error_positions)

    @property
    def key_errors(self) -> dict[str, int]:
        return dict(self._key_errors)

    def _mark_first_keystroke(self) -> None:
        if self._start_time is None:
            self._start_time = self._clock()

    def on_key(self, char: str) -> bool:
        if self.is_complete:
            return False
        self._mark_first_keystroke()
        expected = self._target[self._position]
        self._total_keystrokes += 1
        if char == expected:
            self._position += 1
            return True
        # Wrong key: record the error, then ADVANCE the cursor (forgiving
        # model - the learner types past mistakes instead of being held).
        # ``_ever_errored`` is never cleared, so a later backspace + correct
        # retype yields 0.5 credit (corrected), not 1.0 (first-try).
        self._ever_errored.add(self._position)
        self._error_positions[self._position] = self._error_positions.get(self._position, 0) + 1
        self._key_errors[expected] = self._key_errors.get(expected, 0) + 1
        self._position += 1
        return False

    def on_backspace(self) -> None:
        # Only ``on_key`` starts the timer. Backspace is a no-op at position 0
        # and otherwise decrements AND pops any error recorded at the position
        # being stepped back over - that position can then be re-evaluated on
        # retype. ``_ever_errored`` and ``_key_errors`` are intentionally NOT
        # touched (corrected-credit tracking + cumulative heatmap).
        if self._position > 0:
            self._position -= 1
            self._error_positions.pop(self._position, None)

    def _position_outcomes(self) -> tuple[int, int, int]:
        """Return ``(first_try, corrected, uncorrected)`` counts over typed positions.

        For each position ``p`` in ``range(self._position)``:
        - in ``_ever_errored`` AND in ``_error_positions`` -> uncorrected (0.0)
        - in ``_ever_errored`` AND NOT in ``_error_positions`` -> corrected (0.5)
        - otherwise -> first-try-correct (1.0)
        """
        first_try = 0
        corrected = 0
        uncorrected = 0
        for p in range(self._position):
            was_errored = p in self._ever_errored
            if was_errored and p in self._error_positions:
                uncorrected += 1
            elif was_errored:
                corrected += 1
            else:
                first_try += 1
        return first_try, corrected, uncorrected

    def _credited_chars(self) -> float:
        """Weighted credited chars: first_try * 1.0 + corrected * 0.5."""
        first_try, corrected, _uncorrected = self._position_outcomes()
        return first_try * 1.0 + corrected * 0.5

    def stars(self, wpm_target: float) -> int:
        if not self.is_complete:
            return 0
        two_star_acc, three_star_acc, four_star_acc, five_star_acc = _STAR_ACCURACY_THRESHOLDS
        accuracy = self.accuracy
        wpm = self.net_wpm
        result = 1
        if accuracy >= two_star_acc:
            result = 2
        if accuracy >= three_star_acc:
            result = 3
        if accuracy >= four_star_acc and wpm >= wpm_target:
            result = 4
        if accuracy >= five_star_acc and wpm >= wpm_target:
            result = 5
        return result
