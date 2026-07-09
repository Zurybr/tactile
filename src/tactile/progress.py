"""JSON-backed progress store: stars, best scores, key-error heatmap.

Corrupt or missing progress files never crash the app: a corrupt file is
renamed to `progress.json.bak` and a fresh store is started. A legacy v1 file
is treated as migratable (not corrupt): it is copied to `.bak` and migrated
forward to v2 in memory. Writes are atomic (write `progress.json.tmp`, then
`os.replace` onto the real path).
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tactile.curriculum import Unit

_SCHEMA_VERSION = 2
_DEFAULT_PATH = Path.home() / ".tactile" / "progress.json"


def _default_state() -> dict[str, Any]:
    return {
        "version": _SCHEMA_VERSION,
        "active_layout": None,
        "layouts": {},
        "settings": {},
    }


def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """Forward-only, idempotent v1 -> v2 migration.

    Sets ``version`` to 2 and adds an empty ``settings`` block if absent.
    All existing fields (layouts / lessons / key_errors) are preserved
    verbatim. Running it on already-v2 state is a no-op.
    """
    data["version"] = 2
    data.setdefault("settings", {})
    return data


def _accumulate_key_errors(bucket: dict[str, int], key_errors: dict[str, int]) -> None:
    for key, count in key_errors.items():
        bucket[key] = bucket.get(key, 0) + count


class ProgressStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _DEFAULT_PATH
        self._state = self._load()

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return _default_state()
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("progress file root is not a JSON object")
        except (json.JSONDecodeError, ValueError, OSError, UnicodeDecodeError):
            self._backup_corrupt_file()
            return _default_state()

        version = data.get("version")
        if version == _SCHEMA_VERSION:
            # Accept v2 defensively: an older writer may have omitted settings.
            data.setdefault("settings", {})
            return data
        if version == 1 or version is None:
            # Legacy v1 (or pre-versioning) file: migrate forward, not corrupt.
            self._backup_v1_file()
            return _migrate_v1_to_v2(data)
        # Unknown future version: treat as corrupt.
        self._backup_corrupt_file()
        return _default_state()

    def _backup_corrupt_file(self) -> None:
        backup_path = self._path.with_suffix(self._path.suffix + ".bak")
        try:
            os.replace(self._path, backup_path)
        except OSError:
            pass

    def _backup_v1_file(self) -> None:
        """Copy (not move) the v1 file to `.bak` before the first v2 write.

        A copy preserves the original v1 bytes on disk until a v2 write
        succeeds, so the app stays safe even if `_save` never fires.
        """
        backup_path = self._path.with_suffix(self._path.suffix + ".bak")
        try:
            shutil.copy2(self._path, backup_path)
        except OSError:
            pass

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
        os.replace(tmp_path, self._path)

    @property
    def active_layout(self) -> str | None:
        return self._state.get("active_layout")

    def set_active_layout(self, layout_id: str) -> None:
        self._state["active_layout"] = layout_id
        self._save()

    def _layout_state(self, layout_id: str) -> dict[str, Any]:
        layouts = self._state.setdefault("layouts", {})
        return layouts.setdefault(layout_id, {"lessons": {}, "key_errors": {}})

    def record(
        self,
        layout_id: str,
        unit_id: str,
        stars: int,
        wpm: float,
        accuracy: float,
        key_errors: dict[str, int],
    ) -> None:
        layout_state = self._layout_state(layout_id)
        lessons = layout_state.setdefault("lessons", {})
        existing = lessons.get(unit_id, {"stars": 0, "best_wpm": 0.0, "best_acc": 0.0})
        lessons[unit_id] = {
            "stars": max(existing["stars"], stars),
            "best_wpm": max(existing["best_wpm"], wpm),
            "best_acc": max(existing["best_acc"], accuracy),
        }
        _accumulate_key_errors(layout_state.setdefault("key_errors", {}), key_errors)
        self._save()

    def record_key_errors(self, layout_id: str, key_errors: dict[str, int]) -> None:
        """Accumulate key errors without creating a lesson entry (code practice)."""
        bucket = self._layout_state(layout_id).setdefault("key_errors", {})
        _accumulate_key_errors(bucket, key_errors)
        self._save()

    def _lesson_entry(self, layout_id: str, unit_id: str) -> dict[str, Any] | None:
        return self._state.get("layouts", {}).get(layout_id, {}).get("lessons", {}).get(unit_id)

    def stars_for(self, layout_id: str, unit_id: str) -> int:
        entry = self._lesson_entry(layout_id, unit_id)
        return entry["stars"] if entry else 0

    def best_wpm_for(self, layout_id: str, unit_id: str) -> float:
        entry = self._lesson_entry(layout_id, unit_id)
        return entry["best_wpm"] if entry else 0.0

    def is_unlocked(self, layout_id: str, unit_index: int, units: list[Unit]) -> bool:
        """Any lesson is attemptable. Free navigation: always True.

        The lesson-map cursor highlight uses this to land on the first unit;
        every row is clickable (never disabled). The completion *badge* is a
        separate concern handled by `is_completion_unlocked`.
        """
        return True

    def is_completion_unlocked(
        self, layout_id: str, unit_index: int, units: list[Unit]
    ) -> bool:
        """Completion badge state (the lock icon), derived from `stars >= 2`.

        True iff:
        - `unit_index == 0` (the first unit is always completion-unlocked), OR
        - this unit already has `>= 2` stars, OR
        - any *later* unit `j > unit_index` has `>= 2` stars (the completion
          cascade unlocks every earlier unit across all units globally).

        This is independent of `is_unlocked`: a lesson can be attemptable
        (True) yet still show a locked completion badge (False).
        """
        if unit_index == 0:
            return True
        if self.stars_for(layout_id, units[unit_index].id) >= 2:
            return True
        return any(
            self.stars_for(layout_id, units[j].id) >= 2
            for j in range(unit_index + 1, len(units))
        )

    def get_setting(self, key: str, default: Any) -> Any:
        """Read a value from the `settings` block (or `default` if absent)."""
        return self._state.get("settings", {}).get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        """Write a value into the `settings` block and persist immediately."""
        self._state.setdefault("settings", {})[key] = value
        self._save()

    def key_errors(self, layout_id: str) -> dict[str, int]:
        return dict(self._state.get("layouts", {}).get(layout_id, {}).get("key_errors", {}))
