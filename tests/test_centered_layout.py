"""Pilot tests: practice-screen elements resolve to centered text alignment.

Spec: centered-layout — title, stats, text, and keyboard MUST render with
``text-align: center``. The resolved ``text_align`` style is the semantic
alignment outcome produced by the real Textual CSS cascade, so a CSS revert
(left-align) makes these assertions fail.
"""

from __future__ import annotations

from pathlib import Path

from tactile.app import TactileApp


async def _open_practice(pilot) -> None:
    await pilot.press("enter")  # layout select -> en_us
    await pilot.pause()
    await pilot.press("enter")  # lesson map -> open unit 1
    await pilot.pause()


async def test_practice_widgets_resolve_centered_text_align(tmp_path: Path):
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        await _open_practice(pilot)
        assert app.screen.__class__.__name__ == "PracticeScreen"
        for selector in (
            "#practice-title",
            "#practice-stats",
            "#practice-text",
            "#practice-keyboard",
        ):
            widget = app.screen.query_one(selector)
            assert widget.styles.text_align == "center", selector


async def test_results_body_remains_centered(tmp_path: Path):
    # Regression guard: the already-centered results body must keep resolving
    # to center while we rework practice-screen CSS. Mount ResultsScreen
    # directly (no engine-completion coupling) so the assertion is deterministic.
    from tactile.curriculum import Exercise, Unit
    from tactile.screens.results import ResultsScreen

    unit = Unit(
        id="en_us-01",
        title="Home row: F & J",
        kind="lesson",
        new_chars="fj",
        wpm_target=10.0,
        exercises=(Exercise(text="fj"),),
    )
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        app.push_screen(
            ResultsScreen(
                "en_us", unit, stars=3, wpm=25.0, accuracy=96.0,
                worst_keys=[], record_progress=True,
            )
        )
        await pilot.pause()
        assert app.screen.__class__.__name__ == "ResultsScreen"
        results_body = app.screen.query_one("#results-body")
        assert results_body.styles.text_align == "center"
