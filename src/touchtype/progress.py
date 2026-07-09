"""JSON-backed progress store: stars, best scores, key-error heatmap.

Corrupt or missing progress files never crash the app: a corrupt file is
renamed to `progress.json.bak` and a fresh store is started. Writes are
atomic (write `progress.json.tmp`, then `os.replace` onto the real path).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from touchtype.curriculum import Unit

_SCHEMA_VERSION = 1
_DEFAULT_PATH = Path.home() / ".touchtype" / "progress.json"


def _default_state() -> dict[str, Any]:
    return {"version": _SCHEMA_VERSION, "active_layout": None, "layouts": {}}


class ProgressStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _DEFAULT_PATH
        self._state = self._load()

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return _default_state()
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("version") != _SCHEMA_VERSION:
                raise ValueError("unsupported or missing progress schema version")
        except (json.JSONDecodeError, ValueError, OSError, UnicodeDecodeError):
            self._backup_corrupt_file()
            return _default_state()
        return data

    def _backup_corrupt_file(self) -> None:
        backup_path = self._path.with_suffix(self._path.suffix + ".bak")
        try:
            os.replace(self._path, backup_path)
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
        accumulated = layout_state.setdefault("key_errors", {})
        for key, count in key_errors.items():
            accumulated[key] = accumulated.get(key, 0) + count
        self._save()

    def stars_for(self, layout_id: str, unit_id: str) -> int:
        entry = self._state.get("layouts", {}).get(layout_id, {}).get("lessons", {}).get(unit_id)
        return entry["stars"] if entry else 0

    def best_wpm_for(self, layout_id: str, unit_id: str) -> float:
        entry = self._state.get("layouts", {}).get(layout_id, {}).get("lessons", {}).get(unit_id)
        return entry["best_wpm"] if entry else 0.0

    def is_unlocked(self, layout_id: str, unit_index: int, units: list[Unit]) -> bool:
        if unit_index == 0:
            return True
        previous_unit = units[unit_index - 1]
        return self.stars_for(layout_id, previous_unit.id) >= 2

    def key_errors(self, layout_id: str) -> dict[str, int]:
        return dict(self._state.get("layouts", {}).get(layout_id, {}).get("key_errors", {}))
