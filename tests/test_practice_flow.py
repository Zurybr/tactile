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


async def test_wrong_key_advances_and_records_error(tmp_path: Path):
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        await _open_unit_one(pilot)
        session = app.screen.session
        expected_before = session.expected
        assert expected_before in "fj "  # unit 1 drills f/j/space only

        await pilot.press("q")  # never part of unit 1's pool
        await pilot.pause()
        # Forgiving model: a wrong key ADVANCES the cursor and records the
        # error (the learner types past mistakes).
        assert session.position == 1
        assert 0 in session.error_positions
        assert session.expected != expected_before


async def test_error_to_accuracy_to_stars_to_record_to_unlock_cascade(tmp_path: Path):
    """Full cascade pinned against the new forgiving model: one mid error per
    exercise -> accuracy reflects credited chars -> stars earned -> recorded
    -> completion unlock reflects ``is_unlocked`` (always True after slice 2).
    """
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        await _open_unit_one(pilot)
        unit = app.current_unit
        assert unit is not None

        for exercise in unit.exercises:
            keys = _keys_for(exercise.text)
            # Drill text is long enough to safely split mid-stream.
            mid = max(1, len(keys) // 2)
            # Type the first half perfectly.
            await pilot.press(*keys[:mid])
            # Inject one mid error: wrong key advances; backspace erases it;
            # re-typing from `mid` makes the mid position "corrected" (0.5).
            await pilot.press("q")  # 'q' is never in unit 1's f/j/space pool
            await pilot.pause()
            await pilot.press("backspace")
            await pilot.pause()
            # Finish: re-type mid + the rest (all first-try except `mid`).
            await pilot.press(*keys[mid:])
            await pilot.pause()

        assert app.screen.__class__.__name__ == "ResultsScreen"
        # New formula: one corrected position per exercise -> accuracy < 100%
        # but still high enough to earn at least 1 star.
        assert app.store.stars_for("en_us", unit.id) >= 1
        # Free navigation (slice 2): any lesson is attemptable.
        units = app.curriculum_for("en_us")
        assert app.store.is_unlocked("en_us", 1, units) is True


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


async def test_correct_chars_render_green_wrong_chars_render_red(tmp_path: Path):
    """Typed characters are colored: green for correct, red for uncorrected errors."""
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        await _open_unit_one(pilot)
        session = app.screen.session

        # Type the correct first key (whatever the exercise expects).
        first = session.expected
        key = "space" if first == " " else ("enter" if first == "\n" else first)
        await pilot.press(key)
        await pilot.pause()

        # Type a wrong key (q is never in unit 1's f/j/space pool).
        await pilot.press("q")
        await pilot.pause()

        # Inspect span styles — span.style is a str in this rich version.
        text = app.screen._build_text()
        styles = [str(span.style) for span in text.spans]

        assert any("green" in s for s in styles), \
            f"Expected green for the correct char, got: {styles}"
        assert any("red" in s for s in styles), \
            f"Expected red for the wrong char, got: {styles}"
