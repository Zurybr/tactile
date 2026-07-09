"""Tests for the code-file exercise loader and its CLI/app entry."""

from __future__ import annotations

from pathlib import Path

from touchtype.app import TouchTypeApp
from touchtype.codeload import load_code_exercises
from touchtype.layouts import LAYOUTS

EN_US = LAYOUTS["en_us"]


def test_utf8_file_loads_without_decode_notice(tmp_path: Path):
    path = tmp_path / "sample.py"
    path.write_text("print('hello')\n", encoding="utf-8")
    exercises, notices = load_code_exercises(path, EN_US)
    assert exercises[0].text == "print('hello')"
    assert notices == []


def test_latin1_fallback_adds_notice(tmp_path: Path):
    path = tmp_path / "latin.txt"
    path.write_bytes("caf\xe9 con leche\n".encode("latin-1"))  # invalid as utf-8
    exercises, notices = load_code_exercises(path, EN_US)
    assert "decoded as latin-1" in notices
    assert exercises  # content still loaded


def test_tabs_expanded_indentation_dropped_and_trailing_stripped(tmp_path: Path):
    path = tmp_path / "indent.py"
    path.write_text("def foo():\n\tif x:   \n\t\treturn 1  \n", encoding="utf-8")
    exercises, _ = load_code_exercises(path, EN_US)
    assert exercises[0].text == "def foo():\nif x:\nreturn 1"


def test_blank_lines_are_skipped(tmp_path: Path):
    path = tmp_path / "gaps.py"
    path.write_text("a = 1\n\n   \n\t\nb = 2\n", encoding="utf-8")
    exercises, _ = load_code_exercises(path, EN_US)
    assert exercises[0].text == "a = 1\nb = 2"


def test_eight_line_file_makes_one_exercise(tmp_path: Path):
    path = tmp_path / "eight.txt"
    path.write_text("\n".join(f"line {i}" for i in range(8)) + "\n", encoding="utf-8")
    exercises, _ = load_code_exercises(path, EN_US)
    assert len(exercises) == 1
    assert exercises[0].text.count("\n") == 7


def test_twenty_five_line_file_makes_three_exercises(tmp_path: Path):
    path = tmp_path / "twentyfive.txt"
    path.write_text("\n".join(f"line {i}" for i in range(25)) + "\n", encoding="utf-8")
    exercises, _ = load_code_exercises(path, EN_US)
    assert len(exercises) == 3
    assert exercises[0].text.count("\n") == 9  # 10 lines
    assert exercises[2].text.count("\n") == 4  # remaining 5 lines


def test_file_over_2000_lines_is_truncated_with_notice(tmp_path: Path):
    path = tmp_path / "big.txt"
    path.write_text("\n".join(f"line {i}" for i in range(2005)) + "\n", encoding="utf-8")
    exercises, notices = load_code_exercises(path, EN_US)
    assert "truncated to first 2000 lines" in notices
    assert len(exercises) == 200  # 2000 lines / 10 per exercise


def test_untypable_chars_are_removed_with_single_notice(tmp_path: Path):
    path = tmp_path / "accents.txt"
    path.write_text("café y niño\n", encoding="utf-8")  # é/ñ not on en_us
    exercises, notices = load_code_exercises(path, EN_US)
    assert exercises[0].text == "caf y nio"
    assert "skipped untypable: éñ" in notices


def test_untypable_chars_stay_when_layout_supports_them(tmp_path: Path):
    path = tmp_path / "accents.txt"
    path.write_text("café y niño\n", encoding="utf-8")
    exercises, notices = load_code_exercises(path, LAYOUTS["es_la"])
    assert exercises[0].text == "café y niño"
    assert notices == []


async def test_cli_practice_file_boots_into_code_practice(tmp_path: Path):
    code_file = tmp_path / "snippet.py"
    code_file.write_text("x = 1\ny = 2\n", encoding="utf-8")
    app = TouchTypeApp(progress_path=tmp_path / "p.json", practice_file=code_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.__class__.__name__ == "PracticeScreen"
        assert app.current_unit is not None
        assert app.current_unit.id == "code:snippet.py"
        assert app.current_unit.exercises[0].text == "x = 1\ny = 2"


async def test_completing_code_practice_records_no_lesson_progress(tmp_path: Path):
    code_file = tmp_path / "tiny.txt"
    code_file.write_text("fj\n", encoding="utf-8")
    progress_path = tmp_path / "p.json"
    app = TouchTypeApp(progress_path=progress_path, practice_file=code_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.__class__.__name__ == "PracticeScreen"
        await pilot.press("f", "j")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "ResultsScreen"
        assert app.store.stars_for(app.store.active_layout or "en_us", "code:tiny.txt") == 0


async def test_p_key_on_lesson_map_opens_file_picker(tmp_path: Path):
    from touchtype.progress import ProgressStore

    path = tmp_path / "p.json"
    ProgressStore(path).set_active_layout("en_us")
    app = TouchTypeApp(progress_path=path)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.__class__.__name__ == "LessonMapScreen"
        await pilot.press("p")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "FilePickerScreen"
