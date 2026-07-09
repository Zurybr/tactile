"""Pilot tests for the practice loop: typing, results, and unlocking."""

from __future__ import annotations

from pathlib import Path

from textual.widgets import OptionList

from tactile.app import TactileApp


def _keys_for(text: str) -> list[str]:
    """Map exercise chars to Pilot key names (space -> "space", \\n -> "enter")."""
    keys: list[str] = []
    for char in text:
        if char == " ":
            keys.append("space")
        elif char == "\n":
            keys.append("enter")
        else:
            keys.append(char)
    return keys


async def _open_unit_one(pilot) -> None:
    await pilot.press("enter")  # layout select -> en_us
    await pilot.pause()
    await pilot.press("enter")  # open unit 1 from the lesson map
    await pilot.pause()


async def test_type_through_unit_one_earns_stars_and_shows_results(tmp_path: Path):
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        await _open_unit_one(pilot)
        assert app.screen.__class__.__name__ == "PracticeScreen"
        unit = app.current_unit
        assert unit is not None
        for exercise in unit.exercises:
            await pilot.press(*_keys_for(exercise.text))
            await pilot.pause()
        assert app.screen.__class__.__name__ == "ResultsScreen"
        assert app.store.stars_for("en_us", unit.id) >= 1


async def test_enter_on_results_returns_to_refreshed_map_with_next_unit_unlocked(
    tmp_path: Path,
):
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        await _open_unit_one(pilot)
        unit = app.current_unit
        for exercise in unit.exercises:
            await pilot.press(*_keys_for(exercise.text))
            await pilot.pause()
        assert app.screen.__class__.__name__ == "ResultsScreen"

        await pilot.press("enter")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "LessonMapScreen"

        units = app.curriculum_for("en_us")
        # Perfect typing -> accuracy 100 -> at least 3 stars -> unit 2 unlocked.
        assert app.store.is_unlocked("en_us", 1, units) is True
        option_list = app.screen.query_one(OptionList)
        assert option_list.get_option_at_index(1).disabled is False


async def test_wrong_key_does_not_advance_cursor(tmp_path: Path):
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        await _open_unit_one(pilot)
        session = app.screen.session
        expected_before = session.expected
        assert expected_before in "fj "  # unit 1 drills f/j/space only

        await pilot.press("q")  # never part of unit 1's pool
        await pilot.pause()
        assert session.position == 0
        assert session.expected == expected_before


async def test_escape_returns_to_map_without_recording(tmp_path: Path):
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        await _open_unit_one(pilot)
        assert app.screen.__class__.__name__ == "PracticeScreen"
        unit = app.current_unit
        await pilot.press("f")  # start typing, then bail out
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "LessonMapScreen"
        assert app.store.stars_for("en_us", unit.id) == 0
