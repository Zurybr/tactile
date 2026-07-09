"""Screen: pick a keyboard layout (first run, or later via the 'l' key)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, OptionList

from tactile.layouts import LAYOUTS

_LAYOUT_IDS: list[str] = list(LAYOUTS.keys())


class LayoutSelectScreen(Screen):
    """OptionList of available keyboard layouts."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield OptionList(*(LAYOUTS[layout_id].name for layout_id in _LAYOUT_IDS))
        yield Footer()

    def on_mount(self) -> None:
        option_list = self.query_one(OptionList)
        option_list.focus()
        option_list.highlighted = 0

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        layout_id = _LAYOUT_IDS[event.option_index]
        self.app.store.set_active_layout(layout_id)  # type: ignore[attr-defined]
        self.app.show_lesson_map(layout_id)  # type: ignore[attr-defined]
