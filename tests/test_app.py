"""Pilot tests for the Textual app shell: layout select and lesson map."""

from __future__ import annotations

from pathlib import Path

from textual.widgets import OptionList

from tactile.app import TactileApp
from tactile.progress import ProgressStore


async def test_first_run_shows_layout_select_then_map(tmp_path: Path):
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        assert app.screen.__class__.__name__ == "LayoutSelectScreen"
        await pilot.press("enter")  # pick first option (English US)
        await pilot.pause()
        assert app.screen.__class__.__name__ == "LessonMapScreen"


async def test_second_run_with_active_layout_goes_straight_to_map(tmp_path: Path):
    path = tmp_path / "p.json"
    ProgressStore(path).set_active_layout("en_us")

    app = TactileApp(progress_path=path)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.__class__.__name__ == "LessonMapScreen"


async def test_fresh_store_unlocks_only_first_lesson(tmp_path: Path):
    path = tmp_path / "p.json"
    ProgressStore(path).set_active_layout("en_us")

    app = TactileApp(progress_path=path)
    async with app.run_test() as pilot:
        await pilot.pause()
        units = app.curriculum_for("en_us")
        # Free navigation: every lesson is attemptable (is_unlocked always True).
        assert app.store.is_unlocked("en_us", 0, units) is True
        assert app.store.is_unlocked("en_us", 1, units) is True
        # Only index 0 starts completion-unlocked; later units are still
        # completion-locked on a fresh store (their lock badge is driven by
        # is_completion_unlocked, not is_unlocked).
        assert app.store.is_completion_unlocked("en_us", 0, units) is True
        assert app.store.is_completion_unlocked("en_us", 1, units) is False


async def test_lesson_map_all_rows_clickable_and_lock_icon_reflects_completion(
    tmp_path: Path,
):
    path = tmp_path / "p.json"
    ProgressStore(path).set_active_layout("en_us")

    app = TactileApp(progress_path=path)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.__class__.__name__ == "LessonMapScreen"
        option_list = app.screen.query_one(OptionList)
        units = app.curriculum_for("en_us")

        # Free navigation: every row is clickable, none disabled.
        for index in range(len(units)):
            assert option_list.get_option_at_index(index).disabled is False

        # Completion badge drives the lock icon: index 0 (completion-unlocked)
        # shows no lock; index 1 (completion-locked) shows the lock emoji.
        assert "\U0001f512" not in str(option_list.get_option_at_index(0).prompt)
        assert "\U0001f512" in str(option_list.get_option_at_index(1).prompt)
