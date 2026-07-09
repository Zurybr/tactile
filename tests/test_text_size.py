"""Pilot tests: S/M/L text-size presets on the practice screen.

Spec: text-size-control — three presets cycle via `+`/`-` (wrap S->M->L->S),
adjust container width + text weight (L bold, M normal, S dim), persist in
`settings.size`, and fall back to M on an invalid persisted value.
"""

from __future__ import annotations

from pathlib import Path

from tactile.app import TactileApp
from tactile.progress import ProgressStore


async def _open_practice(pilot) -> None:
    await pilot.press("enter")  # layout select -> en_us
    await pilot.pause()
    await pilot.press("enter")  # lesson map -> open unit 1
    await pilot.pause()


async def test_default_is_medium(tmp_path: Path):
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        await _open_practice(pilot)
        assert app.screen.__class__.__name__ == "PracticeScreen"
        assert app.screen.size_preset == "M"


async def test_plus_cycles_medium_to_large(tmp_path: Path):
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        await _open_practice(pilot)
        assert app.screen.size_preset == "M"
        await pilot.press("+")
        await pilot.pause()
        assert app.screen.size_preset == "L"
        # Large preset applies the size-l class to the practice screen.
        assert app.screen.has_class("size-l")


async def test_minus_cycles_large_down_to_small(tmp_path: Path):
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        await _open_practice(pilot)
        await pilot.press("+")  # M -> L
        await pilot.pause()
        await pilot.press("-")  # L -> M
        await pilot.pause()
        assert app.screen.size_preset == "M"
        await pilot.press("-")  # M -> S
        await pilot.pause()
        assert app.screen.size_preset == "S"
        assert app.screen.has_class("size-s")


async def test_cycling_wraps_at_both_ends(tmp_path: Path):
    app = TactileApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        await _open_practice(pilot)
        # Start at M; reach S, then wrap down to L.
        await pilot.press("-")  # M -> S
        await pilot.pause()
        assert app.screen.size_preset == "S"
        await pilot.press("-")  # S -> L (wrap)
        await pilot.pause()
        assert app.screen.size_preset == "L"
        # From L, plus wraps back to S.
        await pilot.press("+")  # L -> S (wrap)
        await pilot.pause()
        assert app.screen.size_preset == "S"


async def test_size_persists_across_restart(tmp_path: Path):
    path = tmp_path / "p.json"
    app = TactileApp(progress_path=path)
    async with app.run_test() as pilot:
        await _open_practice(pilot)
        await pilot.press("+")  # M -> L
        await pilot.pause()
        assert app.screen.size_preset == "L"

    # A brand-new app on the same store restores the persisted size.
    reopened = TactileApp(progress_path=path)
    async with reopened.run_test() as pilot:
        await _open_practice(pilot)
        assert reopened.screen.size_preset == "L"
        assert reopened.screen.has_class("size-l")


async def test_invalid_stored_size_falls_back_to_medium(tmp_path: Path):
    path = tmp_path / "p.json"
    store = ProgressStore(path)
    store.set_active_layout("en_us")
    store.set_setting("size", "X")  # invalid value outside {S, M, L}

    app = TactileApp(progress_path=path)
    async with app.run_test() as pilot:
        await _open_practice(pilot)
        assert app.screen.size_preset == "M"
        assert app.screen.has_class("size-m")
