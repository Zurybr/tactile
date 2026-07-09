"""Screen: pick a code/text file to practice via a directory tree."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DirectoryTree, Footer, Header


class FilePickerScreen(Screen):
    """DirectoryTree over the current working directory."""

    BINDINGS = [Binding("escape", "cancel", "Back to map")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DirectoryTree(Path.cwd())
        yield Footer()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.app.pop_screen()  # close the picker before opening practice
        self.app.open_code_practice(Path(event.path))  # type: ignore[attr-defined]

    def action_cancel(self) -> None:
        self.app.pop_screen()
