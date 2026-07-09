"""Screen: the core typing practice loop for one curriculum unit."""

from __future__ import annotations

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Static

from touchtype.curriculum import Unit
from touchtype.engine import TypingSession
from touchtype.layouts import Layout
from touchtype.progress import ProgressStore
from touchtype.widgets import KeyboardWidget


class PracticeScreen(Screen):
    """Runs a unit's exercises through a TypingSession, one exercise at a time."""

    BINDINGS = [Binding("escape", "back_to_map", "Back to map")]

    def __init__(
        self,
        unit: Unit,
        exercise_index: int,
        layout: Layout,
        store: ProgressStore,
    ) -> None:
        super().__init__()
        self.unit = unit
        self.exercise_index = exercise_index
        # Note: `layout` is a reserved Textual Widget property, so the
        # keyboard layout is stored under a different attribute name.
        self.keyboard_layout = layout
        self.store = store
        self.session = TypingSession(unit.exercises[exercise_index].text)
        self._exercise_results: list[tuple[float, float, int]] = []  # (acc, net_wpm, stars)
        self._unit_key_errors: dict[str, int] = {}
        self._last_key_was_wrong = False

    def compose(self) -> ComposeResult:
        yield Static(id="practice-title")
        yield Static(id="practice-stats")
        yield Static(id="practice-text")
        yield KeyboardWidget(self.keyboard_layout, id="practice-keyboard")
        yield Footer()

    def on_mount(self) -> None:
        self._stats_timer = self.set_interval(0.5, self._update_stats)
        self._refresh_all()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            return  # let the screen binding handle navigation
        if event.key == "enter":
            self._last_key_was_wrong = self.session.on_key("\n") is False
        elif event.key == "backspace":
            self.session.on_backspace()
            self._last_key_was_wrong = False
        elif event.character is not None and event.is_printable:
            self._last_key_was_wrong = self.session.on_key(event.character) is False
        else:
            return
        event.stop()
        if self.session.is_complete:
            self._finish_exercise()
        else:
            self._refresh_text()
            self.query_one(KeyboardWidget).highlight(self.session.expected)

    def action_back_to_map(self) -> None:
        self.app.practice_abort()  # type: ignore[attr-defined]

    def _finish_exercise(self) -> None:
        session = self.session
        self._exercise_results.append(
            (session.accuracy, session.net_wpm, session.stars(self.unit.wpm_target))
        )
        for key, count in session.key_errors.items():
            self._unit_key_errors[key] = self._unit_key_errors.get(key, 0) + count

        next_index = self.exercise_index + 1
        if next_index < len(self.unit.exercises):
            self.exercise_index = next_index
            self.session = TypingSession(self.unit.exercises[next_index].text)
            self._last_key_was_wrong = False
            self._refresh_all()
            return

        self._stats_timer.stop()
        accuracies = [result[0] for result in self._exercise_results]
        wpms = [result[1] for result in self._exercise_results]
        stars = min(result[2] for result in self._exercise_results)
        accuracy = sum(accuracies) / len(accuracies)
        wpm = sum(wpms) / len(wpms)
        worst_keys = sorted(self._unit_key_errors.items(), key=lambda kv: (-kv[1], kv[0]))[:3]

        self.store.record(
            self.keyboard_layout.id,
            self.unit.id,
            stars=stars,
            wpm=wpm,
            accuracy=accuracy,
            key_errors=self._unit_key_errors,
        )
        self.app.show_results(  # type: ignore[attr-defined]
            self.keyboard_layout.id, self.unit, stars, wpm, accuracy, worst_keys
        )

    def _refresh_all(self) -> None:
        title = self.query_one("#practice-title", Static)
        title.update(
            f"{self.unit.title} - exercise {self.exercise_index + 1}/{len(self.unit.exercises)}"
        )
        self._update_stats()
        self._refresh_text()
        self.query_one(KeyboardWidget).highlight(self.session.expected)

    def _update_stats(self) -> None:
        stats = self.query_one("#practice-stats", Static)
        stats.update(f"WPM {self.session.net_wpm:5.1f}   ACC {self.session.accuracy:5.1f}%")

    def _refresh_text(self) -> None:
        target = self.unit.exercises[self.exercise_index].text
        position = self.session.position
        text = Text()
        text.append(target[:position], style="green")
        if position < len(target):
            cursor_char = target[position]
            cursor_display = "⏎\n" if cursor_char == "\n" else cursor_char
            cursor_style = "reverse red" if self._last_key_was_wrong else "reverse"
            text.append(cursor_display, style=cursor_style)
            text.append(target[position + 1 :], style="dim")
        self.query_one("#practice-text", Static).update(text)
