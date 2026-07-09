# Progress

`progress.py` is the persistence layer: a JSON-backed `ProgressStore` that
tracks active layout, per-unit stars/best scores, and a per-key error
heatmap. It is the only module that writes to the user's home directory.

## `ProgressStore`

```python
class ProgressStore:
    def __init__(self, path: Path | None = None)   # default: ~/.tactile/progress.json
    active_layout: str | None                       # property
    def set_active_layout(self, layout_id: str) -> None
    def record(self, layout_id, unit_id, stars, wpm, accuracy, key_errors) -> None
    def record_key_errors(self, layout_id, key_errors) -> None   # code practice only
    def stars_for(self, layout_id, unit_id) -> int               # 0 when unseen
    def best_wpm_for(self, layout_id, unit_id) -> float          # 0.0 when unseen
    def is_unlocked(self, layout_id, unit_index, units) -> bool
    def key_errors(self, layout_id) -> dict[str, int]
```

The store loads on construction. If the file is missing, it starts fresh.
The constructor accepts an optional `path` so tests pass a `tmp_path` and
never touch the real progress file.

## JSON schema

Schema version 1. Stored at `~/.tactile/progress.json`:

```json
{
  "version": 1,
  "active_layout": "en_us",
  "layouts": {
    "en_us": {
      "lessons": {
        "en_us-01": {"stars": 4, "best_wpm": 32.5, "best_acc": 97.2},
        "en_us-02": {"stars": 2, "best_wpm": 18.0, "best_acc": 91.0}
      },
      "key_errors": {"f": 12, ";": 40, "a": 3}
    },
    "es_la": {
      "lessons": {},
      "key_errors": {}
    }
  }
}
```

| Field | Type | Meaning |
|-------|------|---------|
| `version` | `int` | schema version, currently `1`. A mismatch triggers the corrupt-file path. |
| `active_layout` | `str \| null` | the last layout the user picked; `null` on first run. |
| `layouts.<id>.lessons.<unit_id>.stars` | `int` | best star rating (0-5) for that unit. |
| `layouts.<id>.lessons.<unit_id>.best_wpm` | `float` | best net WPM achieved. |
| `layouts.<id>.lessons.<unit_id>.best_acc` | `float` | best accuracy achieved. |
| `layouts.<id>.key_errors.<char>` | `int` | accumulated wrong attempts for that expected char. |

See [reference/progress-schema.md](../reference/progress-schema.md) for the
authoritative field listing.

## Best-keeping

`record()` never lowers a unit's recorded bests. Stars, WPM, and accuracy
are kept with `max(existing, new)`, so a worse replay does not regress your
progress. The key-error counts, however, **accumulate** — every wrong
attempt is added to the heatmap regardless of whether the run was a best.

```python
lessons[unit_id] = {
    "stars": max(existing["stars"], stars),
    "best_wpm": max(existing["best_wpm"], wpm),
    "best_acc": max(existing["best_acc"], accuracy),
}
_accumulate_key_errors(layout_state.setdefault("key_errors", {}), key_errors)
```

### `record_key_errors` (code practice)

Code/text file practice is **not** recorded as lesson progress — it has no
`unit_id` in the curriculum and `record_progress=False`. But the key-error
heatmap should still benefit from the practice, so
`PracticeScreen` calls `record_key_errors(layout_id, key_errors)` instead.
This accumulates into `key_errors` without creating a lesson entry.

## Atomic writes

Writes never leave a half-written file visible:

```python
def _save(self) -> None:
    self._path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
    os.replace(tmp_path, self._path)        # atomic on the same filesystem
```

`os.replace` is atomic on Windows and POSIX when source and destination are
on the same filesystem. A test asserts no `.tmp` file is left behind after
a write.

## Corrupt-file handling

A missing, unparseable, or wrong-version file never crashes the app:

```python
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
```

The corrupt file is renamed to `progress.json.bak` (via `os.replace`), and a
fresh default state is started:

```python
def _backup_corrupt_file(self) -> None:
    backup_path = self._path.with_suffix(self._path.suffix + ".bak")
    try:
        os.replace(self._path, backup_path)
    except OSError:
        pass
```

So a user who deletes or corrupts their file loses their stars, but the app
keeps running. Deleting `~/.tactile/progress.json` resets all progress.

## Sequential unlocking

```python
def is_unlocked(self, layout_id, unit_index, units) -> bool:
    if unit_index == 0:
        return True
    previous_unit = units[unit_index - 1]
    return self.stars_for(layout_id, previous_unit.id) >= 2
```

- The first unit (index 0) is always unlocked.
- Every later unit unlocks when the **previous** unit has >= 2 stars.
- Replays are always allowed (locked units are disabled in the lesson map,
  but an unlocked unit stays replayable even after you move on).

The lesson map reads `is_unlocked` per row and disables locked rows; the
cursor lands on the first unlocked unit on mount. When a results screen
returns to the map, `results_continue` calls `refresh_options()` so a newly
earned 2+ stars immediately unlocks the next row.
