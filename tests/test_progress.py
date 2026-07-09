"""Tests for the JSON progress store: persistence, bests, unlocking."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from tactile.progress import ProgressStore, _migrate_v1_to_v2


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


def test_unlock_logic_any_lesson_is_attemptable(tmp_path: Path):
    # Free navigation: is_unlocked is True for every unit regardless of stars.
    store = ProgressStore(tmp_path / "progress.json")
    units = [SimpleNamespace(id=f"en_us-{i:02d}") for i in range(10)]

    for index in range(len(units)):
        assert store.is_unlocked("en_us", index, units) is True

    # Completing an earlier unit with 1 star still leaves every unit attemptable.
    store.record("en_us", "en_us-00", stars=1, wpm=10.0, accuracy=80.0, key_errors={})
    for index in range(len(units)):
        assert store.is_unlocked("en_us", index, units) is True


def test_completion_unlocks_all_previous_globally(tmp_path: Path):
    # Completing >= 2 stars at a later unit unlocks every earlier unit's
    # completion badge across all units (the completion cascade). Below 2 stars
    # does not trigger it.
    store = ProgressStore(tmp_path / "progress.json")
    units = [SimpleNamespace(id=f"en_us-{i:02d}") for i in range(10)]

    # Nothing completed yet: only index 0 is completion-unlocked by default.
    assert store.is_completion_unlocked("en_us", 0, units) is True
    for index in range(1, len(units)):
        assert store.is_completion_unlocked("en_us", index, units) is False

    # 1 star somewhere must NOT unlock anything via the completion cascade.
    store.record("en_us", "en_us-03", stars=1, wpm=10.0, accuracy=80.0, key_errors={})
    for index in range(1, len(units)):
        if index == 3:
            continue
        assert store.is_completion_unlocked("en_us", index, units) is False

    # >= 2 stars at unit index 5 unlocks every earlier index (< 5).
    store.record("en_us", "en_us-05", stars=2, wpm=18.0, accuracy=92.0, key_errors={})
    for index in range(5):
        assert store.is_completion_unlocked("en_us", index, units) is True
    # Index 5 itself is completion-unlocked (it has >= 2 stars).
    assert store.is_completion_unlocked("en_us", 5, units) is True
    # Later indices with no completion stay completion-locked.
    assert store.is_completion_unlocked("en_us", 6, units) is False


def test_fresh_store_is_v2_with_settings(tmp_path: Path):
    path = tmp_path / "progress.json"
    ProgressStore(path).set_active_layout("en_us")  # forces a save
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["version"] == 2
    assert raw["settings"] == {}


def test_v1_file_migrates_to_v2_preserving_stars_and_key_errors(tmp_path: Path):
    path = tmp_path / "progress.json"
    v1_state = {
        "version": 1,
        "active_layout": "en_us",
        "layouts": {
            "en_us": {
                "lessons": {
                    "en_us-01": {"stars": 4, "best_wpm": 30.0, "best_acc": 96.0}
                },
                "key_errors": {"f": 12},
            }
        },
    }
    path.write_text(json.dumps(v1_state), encoding="utf-8")

    store = ProgressStore(path)

    # A v1 file is NOT corrupt: it is copied to .bak before migration.
    backup_path = tmp_path / "progress.json.bak"
    assert backup_path.exists()
    assert json.loads(backup_path.read_text(encoding="utf-8"))["version"] == 1

    # Migration: version bumped, settings added, stars + key_errors preserved.
    assert store.stars_for("en_us", "en_us-01") == 4
    assert store.key_errors("en_us") == {"f": 12}
    assert store.get_setting("size", "M") == "M"  # settings block present


def test_migration_is_idempotent(tmp_path: Path):
    # Running the migrator twice on already-migrated state is a no-op:
    # byte-identical output.
    data = {
        "version": 1,
        "active_layout": "en_us",
        "layouts": {"en_us": {"lessons": {"en_us-01": {"stars": 4}}, "key_errors": {}}},
    }
    once = _migrate_v1_to_v2(json.loads(json.dumps(data)))
    twice = _migrate_v1_to_v2(json.loads(json.dumps(once)))
    assert once == twice == {
        "version": 2,
        "active_layout": "en_us",
        "layouts": {"en_us": {"lessons": {"en_us-01": {"stars": 4}}, "key_errors": {}}},
        "settings": {},
    }


def test_v2_round_trip_preserves_settings_and_bests(tmp_path: Path):
    path = tmp_path / "progress.json"
    store = ProgressStore(path)
    store.record("en_us", "en_us-01", stars=3, wpm=25.0, accuracy=96.0, key_errors={"f": 2})
    store.set_setting("size", "L")

    reloaded = ProgressStore(path)
    assert reloaded.stars_for("en_us", "en_us-01") == 3
    assert reloaded.best_wpm_for("en_us", "en_us-01") == 25.0
    assert reloaded.key_errors("en_us") == {"f": 2}
    assert reloaded.get_setting("size", "M") == "L"


def test_corrupt_file_still_backed_up_and_not_treated_as_v1(tmp_path: Path):
    # Genuinely unparseable JSON goes through the corrupt-file path
    # (rename to .bak + fresh v2), NOT the v1 migration path.
    path = tmp_path / "progress.json"
    path.write_text("{not valid json", encoding="utf-8")

    store = ProgressStore(path)

    backup_path = tmp_path / "progress.json.bak"
    assert backup_path.exists()
    assert backup_path.read_text(encoding="utf-8") == "{not valid json"
    # The fresh store is a real v2 store, usable immediately.
    assert store.active_layout is None
    store.set_setting("size", "L")
    assert ProgressStore(path).get_setting("size", "M") == "L"


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
