"""Reusable widgets: the on-screen keyboard with next-key and finger hints."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from touchtype.layouts import Layout

_STAR_SLOTS = 5


def render_stars(stars: int) -> str:
    """Render a 5-slot star bar, e.g. 3 -> '★★★☆☆'."""
    return "★" * stars + "☆" * (_STAR_SLOTS - stars)


class KeyboardWidget(Static):
    """Renders the layout's key caps and highlights the next expected key."""

    def __init__(self, layout: Layout, **kwargs) -> None:
        super().__init__(**kwargs)
        # Note: `layout` is a reserved Textual Widget property, so the
        # keyboard layout is stored under a different attribute name.
        self.keyboard_layout = layout
        self._highlight_char: str | None = None

    def on_mount(self) -> None:
        self.update(self._render_keyboard())

    def highlight(self, char: str | None) -> None:
        self._highlight_char = char
        self.update(self._render_keyboard())

    def _hint_and_target(self) -> tuple[str, tuple[int, int] | None]:
        char = self._highlight_char
        if char is None:
            return "", None
        if char == " ":
            return "thumb - Space", None
        if char == "\n":
            return "right pinky - Enter", None
        info = self.keyboard_layout.char_map.get(char)
        if info is None:
            return f"not on this layout: {char!r}", None
        cap = self.keyboard_layout.rows[info.row][info.col]
        if info.modifier == "shift":
            return f"{info.finger} - Shift + {cap}", (info.row, info.col)
        if info.modifier == "altgr":
            return f"{info.finger} - AltGr + {cap}", (info.row, info.col)
        if info.modifier == "dead":
            return f"{info.finger} - {info.hint}", (info.row, info.col)
        return info.finger, (info.row, info.col)

    def _render_keyboard(self) -> Text:
        hint, target = self._hint_and_target()
        text = Text()
        for row_index, row in enumerate(self.keyboard_layout.rows):
            text.append(" " * row_index)  # stagger rows like a physical keyboard
            for col_index, cap in enumerate(row):
                highlighted = (row_index, col_index) == target
                style = "bold reverse" if highlighted else "dim"
                text.append(f" {cap} ", style=style)
            text.append("\n")
        text.append(hint or " ", style="italic")
        return text
