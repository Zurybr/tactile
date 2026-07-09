"""Tests for the JSON progress store: persistence, bests, unlocking."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from tactile.progress import ProgressStore


def test_fresh_store_has_defaults(tmp_path: Path):
    store = ProgressStore(tmp_path / "progress.json")
    assert store.active_layout is None
    assert store.stars_for("en_us", "en_us-01") == 0
    assert store.key_errors("en_us") == {}


def test_set_active_layout_persists(tmp_path: Path):
    path = tmp_path / "progress.json"
    store = ProgressStore(path)
    store.set_active_layout("en_us")
    reloaded = ProgressStore(path)
    assert reloaded.active_layout == "en_us"


def test_record_and_reload_round_trip(tmp_path: Path):
    path = tmp_path / "progress.json"
    store = ProgressStore(path)
    store.record("en_us", "en_us-01", stars=3, wpm=25.0, accuracy=96.0, key_errors={"f": 2})

    reloaded = ProgressStore(path)
    assert reloaded.stars_for("en_us", "en_us-01") == 3
    assert reloaded.key_errors("en_us") == {"f": 2}


def test_record_keeps_best_stars_and_wpm_but_still_accumulates_key_errors(tmp_path: Path):
    store = ProgressStore(tmp_path / "progress.json")
    store.record("en_us", "en_us-01", stars=4, wpm=30.0, accuracy=98.0, key_errors={"f": 1})
    # A later, worse attempt must not lower the recorded bests.
    store.record("en_us", "en_us-01", stars=2, wpm=15.0, accuracy=90.0, key_errors={"f": 3, "j": 1})

    assert store.stars_for("en_us", "en_us-01") == 4
    assert store.key_errors("en_us") == {"f": 4, "j": 1}


def test_unlock_logic_first_unit_always_unlocked_second_needs_two_stars(tmp_path: Path):
    store = ProgressStore(tmp_path / "progress.json")
    units = [SimpleNamespace(id="en_us-01"), SimpleNamespace(id="en_us-02")]

    assert store.is_unlocked("en_us", 0, units) is True
    assert store.is_unlocked("en_us", 1, units) is False

    store.record("en_us", "en_us-01", stars=1, wpm=10.0, accuracy=80.0, key_errors={})
    assert store.is_unlocked("en_us", 1, units) is False

    store.record("en_us", "en_us-01", stars=2, wpm=12.0, accuracy=91.0, key_errors={})
    assert store.is_unlocked("en_us", 1, units) is True


def test_corrupt_file_is_backed_up_and_store_starts_fresh(tmp_path: Path):
    path = tmp_path / "progress.json"
    path.write_text("{not valid json", encoding="utf-8")

    store = ProgressStore(path)

    backup_path = tmp_path / "progress.json.bak"
    assert backup_path.exists()
    assert backup_path.read_text(encoding="utf-8") == "{not valid json"
    assert store.active_layout is None

    # Store must remain fully usable after recovering from corruption.
    store.set_active_layout("en_us")
    assert ProgressStore(path).active_layout == "en_us"


def test_best_wpm_for_returns_zero_when_unseen_and_best_after_record(tmp_path: Path):
    store = ProgressStore(tmp_path / "progress.json")
    assert store.best_wpm_for("en_us", "en_us-01") == 0.0

    store.record("en_us", "en_us-01", stars=3, wpm=28.5, accuracy=95.0, key_errors={})
    assert store.best_wpm_for("en_us", "en_us-01") == 28.5

    # A later, worse WPM must not overwrite the best.
    store.record("en_us", "en_us-01", stars=3, wpm=20.0, accuracy=95.0, key_errors={})
    assert store.best_wpm_for("en_us", "en_us-01") == 28.5


def test_record_key_errors_accumulates_without_touching_lessons(tmp_path: Path):
    path = tmp_path / "progress.json"
    store = ProgressStore(path)
    store.record_key_errors("en_us", {"f": 2, "j": 1})
    store.record_key_errors("en_us", {"f": 1})

    reloaded = ProgressStore(path)
    assert reloaded.key_errors("en_us") == {"f": 3, "j": 1}
    # No lesson entry may appear as a side effect.
    assert reloaded.stars_for("en_us", "code:sample.py") == 0
    raw = path.read_text(encoding="utf-8")
    assert '"lessons": {}' in raw


def test_atomic_write_does_not_leave_tmp_file_behind(tmp_path: Path):
    path = tmp_path / "progress.json"
    store = ProgressStore(path)
    store.record("en_us", "en_us-01", stars=1, wpm=10.0, accuracy=80.0, key_errors={"f": 1})

    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []
    assert path.exists()
