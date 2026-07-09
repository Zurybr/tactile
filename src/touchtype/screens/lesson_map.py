"""Screen: scrollable map of a layout's curriculum units."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, OptionList
from textual.widgets.option_list import Option

from touchtype.widgets import render_stars

if TYPE_CHECKING:
    from touchtype.curriculum import Unit
    from touchtype.progress import ProgressStore


class LessonMapScreen(Screen):
    """OptionList of a layout's units, showing lock state, stars, and best WPM."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("l", "change_layout", "Change layout"),
        Binding("p", "practice_file", "Practice a file"),
    ]

    def __init__(self, layout_id: str) -> None:
        super().__init__()
        self.layout_id = layout_id

    def compose(self) -> ComposeResult:
        yield Header()
        yield OptionList()
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_options()

    def refresh_options(self) -> None:
        units: list[Unit] = self.app.curriculum_for(self.layout_id)  # type: ignore[attr-defined]
        store: ProgressStore = self.app.store  # type: ignore[attr-defined]
        option_list = self.query_one(OptionList)
        option_list.clear_options()

        first_unlocked = 0
        for index, unit in enumerate(units):
            unlocked = store.is_unlocked(self.layout_id, index, units)
            if unlocked:
                first_unlocked = index
            stars = store.stars_for(self.layout_id, unit.id)
            best_wpm = store.best_wpm_for(self.layout_id, unit.id)
            option_list.add_option(
                Option(_format_row(unit, stars, best_wpm, unlocked), disabled=not unlocked)
            )

        option_list.focus()
        option_list.highlighted = first_unlocked

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        units: list[Unit] = self.app.curriculum_for(self.layout_id)  # type: ignore[attr-defined]
        unit = units[event.option_index]
        self.app.open_practice(self.layout_id, unit)  # type: ignore[attr-defined]

    def action_change_layout(self) -> None:
        self.app.show_layout_select()  # type: ignore[attr-defined]

    def action_practice_file(self) -> None:
        self.app.show_file_picker()  # type: ignore[attr-defined]

    def action_quit(self) -> None:
        self.app.exit()


def _format_row(unit: Unit, stars: int, best_wpm: float, unlocked: bool) -> str:
    lock = " " if unlocked else "\U0001f512"
    wpm_str = f"{best_wpm:.0f} wpm" if best_wpm else "--- wpm"
    return f"{lock} {render_stars(stars)}  {unit.title}  ({wpm_str})"
