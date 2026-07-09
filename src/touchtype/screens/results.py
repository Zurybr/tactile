"""Screen: unit results - stars earned, WPM, accuracy, worst keys."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Static

if TYPE_CHECKING:
    from touchtype.curriculum import Unit

_STAR_SLOTS = 5


class ResultsScreen(Screen):
    """Shows the aggregate result of a completed unit."""

    BINDINGS = [
        Binding("r", "retry", "Retry unit"),
        Binding("enter", "continue", "Back to map"),
    ]

    def __init__(
        self,
        layout_id: str,
        unit: Unit,
        stars: int,
        wpm: float,
        accuracy: float,
        worst_keys: list[tuple[str, int]],
    ) -> None:
        super().__init__()
        self.layout_id = layout_id
        self.unit = unit
        self.stars = stars
        self.wpm = wpm
        self.accuracy = accuracy
        self.worst_keys = worst_keys

    def compose(self) -> ComposeResult:
        star_line = "★" * self.stars + "☆" * (_STAR_SLOTS - self.stars)
        lines = [
            self.unit.title,
            "",
            star_line,
            f"WPM {self.wpm:.1f}",
            f"Accuracy {self.accuracy:.1f}%",
        ]
        if self.worst_keys:
            keys = ", ".join(f"{key!r} x{count}" for key, count in self.worst_keys)
            lines.append(f"Worst keys: {keys}")
        else:
            lines.append("No errors - flawless run!")
        yield Static("\n".join(lines), id="results-body")
        yield Footer()

    def action_retry(self) -> None:
        self.app.results_retry(self.layout_id, self.unit)  # type: ignore[attr-defined]

    def action_continue(self) -> None:
        self.app.results_continue()  # type: ignore[attr-defined]
