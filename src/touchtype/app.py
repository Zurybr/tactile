"""Textual application shell: wires progression, content, and screens."""

from __future__ import annotations

from pathlib import Path

from textual.app import App

from touchtype.codeload import load_code_exercises
from touchtype.curriculum import Unit, build_curriculum, load_wordlist
from touchtype.layouts import LAYOUTS
from touchtype.progress import ProgressStore
from touchtype.screens.file_picker import FilePickerScreen
from touchtype.screens.layout_select import LayoutSelectScreen
from touchtype.screens.lesson_map import LessonMapScreen
from touchtype.screens.practice import PracticeScreen
from touchtype.screens.results import ResultsScreen


class TouchTypeApp(App):
    """touchtype: a TUI touch-typing trainer."""

    CSS_PATH = "styles.tcss"
    TITLE = "touchtype"

    def __init__(
        self, progress_path: Path | None = None, practice_file: Path | None = None
    ) -> None:
        super().__init__()
        self.store = ProgressStore(progress_path)
        self.practice_file = practice_file
        self.current_unit: Unit | None = None
        self._curricula: dict[str, list[Unit]] = {}

    def curriculum_for(self, layout_id: str) -> list[Unit]:
        if layout_id not in self._curricula:
            layout = LAYOUTS[layout_id]
            words = load_wordlist(layout_id)
            self._curricula[layout_id] = build_curriculum(layout, words)
        return self._curricula[layout_id]

    def on_mount(self) -> None:
        if self.practice_file is not None:
            # CLI `touchtype practice <path>`: land straight in code practice
            # over the active layout (en_us fallback), with the lesson map
            # underneath so escape/results navigation works as usual.
            layout_id = self.store.active_layout or "en_us"
            self.show_lesson_map(layout_id)
            self.open_code_practice(self.practice_file)
        elif self.store.active_layout is None:
            self.show_layout_select()
        else:
            self.show_lesson_map(self.store.active_layout)

    def show_layout_select(self) -> None:
        self.push_screen(LayoutSelectScreen())

    def show_lesson_map(self, layout_id: str) -> None:
        self.push_screen(LessonMapScreen(layout_id))

    def show_file_picker(self) -> None:
        self.push_screen(FilePickerScreen())

    def open_practice(self, layout_id: str, unit: Unit) -> None:
        self.current_unit = unit
        record_progress = not unit.id.startswith("code:")
        self.push_screen(
            PracticeScreen(
                unit=unit,
                exercise_index=0,
                layout=LAYOUTS[layout_id],
                store=self.store,
                record_progress=record_progress,
            )
        )

    def open_code_practice(self, path: Path) -> None:
        layout_id = self.store.active_layout or "en_us"
        try:
            exercises, notices = load_code_exercises(path, LAYOUTS[layout_id])
        except OSError as error:
            self.notify(f"Could not read {path}: {error}", severity="error")
            return
        if not exercises:
            self.notify(f"No typable content in {path}", severity="warning")
            return
        unit = Unit(
            id=f"code:{path.name}",
            title=f"Code practice: {path.name}",
            kind="lesson",
            new_chars="",
            wpm_target=30.0,
            exercises=tuple(exercises),
        )
        self.open_practice(layout_id, unit)
        for notice in notices:
            self.notify(notice)

    def show_results(
        self,
        layout_id: str,
        unit: Unit,
        stars: int,
        wpm: float,
        accuracy: float,
        worst_keys: list[tuple[str, int]],
    ) -> None:
        self.push_screen(ResultsScreen(layout_id, unit, stars, wpm, accuracy, worst_keys))

    def practice_abort(self) -> None:
        self.pop_screen()  # PracticeScreen -> back to the lesson map

    def results_continue(self) -> None:
        self.pop_screen()  # ResultsScreen
        self.pop_screen()  # PracticeScreen
        screen = self.screen
        if isinstance(screen, LessonMapScreen):
            screen.refresh_options()

    def results_retry(self, layout_id: str, unit: Unit) -> None:
        self.pop_screen()  # ResultsScreen
        self.pop_screen()  # PracticeScreen
        self.open_practice(layout_id, unit)
