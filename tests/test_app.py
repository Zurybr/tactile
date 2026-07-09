"""Pilot tests for the Textual app shell: layout select and lesson map."""

from __future__ import annotations

from pathlib import Path

from touchtype.app import TouchTypeApp
from touchtype.progress import ProgressStore


async def test_first_run_shows_layout_select_then_map(tmp_path: Path):
    app = TouchTypeApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        assert app.screen.__class__.__name__ == "LayoutSelectScreen"
        await pilot.press("enter")  # pick first option (English US)
        await pilot.pause()
        assert app.screen.__class__.__name__ == "LessonMapScreen"


async def test_second_run_with_active_layout_goes_straight_to_map(tmp_path: Path):
    path = tmp_path / "p.json"
    ProgressStore(path).set_active_layout("en_us")

    app = TouchTypeApp(progress_path=path)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.__class__.__name__ == "LessonMapScreen"


async def test_fresh_store_unlocks_only_first_lesson(tmp_path: Path):
    path = tmp_path / "p.json"
    ProgressStore(path).set_active_layout("en_us")

    app = TouchTypeApp(progress_path=path)
    async with app.run_test() as pilot:
        await pilot.pause()
        units = app.curriculum_for("en_us")
        assert app.store.is_unlocked("en_us", 0, units) is True
        assert app.store.is_unlocked("en_us", 1, units) is False
