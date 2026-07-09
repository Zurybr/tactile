"""Pure typing session engine.

Implements the edclub-style cursor model: the cursor never advances on a
wrong key, and every wrong attempt counts against accuracy. No I/O, no
Textual dependency - this module is pure domain logic.
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
        self._correct_keystrokes = 0
        self._error_positions: dict[int, int] = {}
        self._key_errors: dict[str, int] = {}

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
        return self._wpm(self._position)

    def _wpm(self, char_count: int) -> float:
        minutes = self.elapsed / 60.0
        if minutes <= 0:
            return 0.0
        return (char_count / 5) / minutes

    @property
    def accuracy(self) -> float:
        if self._total_keystrokes == 0:
            return 100.0
        return (self._correct_keystrokes / self._total_keystrokes) * 100

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
            self._correct_keystrokes += 1
            self._position += 1
            return True
        self._error_positions[self._position] = self._error_positions.get(self._position, 0) + 1
        self._key_errors[expected] = self._key_errors.get(expected, 0) + 1
        return False

    def on_backspace(self) -> None:
        self._mark_first_keystroke()
        if self._position > 0:
            self._position -= 1

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
