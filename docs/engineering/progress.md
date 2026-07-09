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
    def is_unlocked(self, layout_id, unit_index, units) -> bool  # always True (free nav)
    def is_completion_unlocked(self, layout_id, unit_index, units) -> bool
    def get_setting(self, key, default)                          # read settings block
    def set_setting(self, key, value) -> None                    # write + persist
    def key_errors(self, layout_id) -> dict[str, int]
```

The store loads on construction. If the file is missing, it starts fresh.
The constructor accepts an optional `path` so tests pass a `tmp_path` and
never touch the real progress file.

## JSON schema

Schema version 2. Stored at `~/.tactile/progress.json`:

```json
{
  "version": 2,
  "active_layout": "en_us",
  "settings": {
    "size": "M"
  },
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
| `version` | `int` | schema version, currently `2`. A `1`/missing version migrates forward on load; an unparseable / non-object / unknown-future version triggers the corrupt-file path. |
| `active_layout` | `str \| null` | the last layout the user picked; `null` on first run. |
| `settings` | `object` | free-form UI preferences (added in v2). Holds `size` (the S/M/L preset). |
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

## Corrupt-file and legacy-file handling

A missing, unparseable, or wrong-version file never crashes the app. The
load path branches on the parsed `version`:

```python
def _load(self) -> dict[str, Any]:
    if not self._path.exists():
        return _default_state()                          # fresh v2
    try:
        data = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("progress file root is not a JSON object")
    except (json.JSONDecodeError, ValueError, OSError, UnicodeDecodeError):
        self._backup_corrupt_file()                      # rename to .bak
        return _default_state()

    version = data.get("version")
    if version == _SCHEMA_VERSION:                       # v2
        data.setdefault("settings", {})
        return data
    if version == 1 or version is None:                  # legacy v1
        self._backup_v1_file()                           # COPY to .bak
        return _migrate_v1_to_v2(data)
    self._backup_corrupt_file()                          # unknown future
    return _default_state()
```

A truly corrupt file (unparseable / non-object / unknown-future-version) is
**renamed** to `progress.json.bak` and a fresh default state starts:

```python
def _backup_corrupt_file(self) -> None:
    backup_path = self._path.with_suffix(self._path.suffix + ".bak")
    try:
        os.replace(self._path, backup_path)              # move
    except OSError:
        pass
```

A legacy **v1** file is **not** corrupt — it is migrated forward. The v1
file is **copied** (not moved) to `.bak` before the first v2 write, so the
original bytes survive even if a save never fires:

```python
def _backup_v1_file(self) -> None:
    backup_path = self._path.with_suffix(self._path.suffix + ".bak")
    try:
        shutil.copy2(self._path, backup_path)            # copy
    except OSError:
        pass
```

So a user who deletes or corrupts their file loses their stars, but the app
keeps running. A v1 user keeps their stars/bests through the v1->v2
migration. Deleting `~/.tactile/progress.json` resets all progress.

### v1 -> v2 migration

```python
def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    data["version"] = 2
    data.setdefault("settings", {})
    return data
```

Forward-only and idempotent: re-running on already-v2 state is a no-op
(`version` stays `2`, `settings` stays present). All `layouts` / `lessons` /
`key_errors` are preserved verbatim — migration only adds the `settings`
block and bumps the version. A test asserts that running the migrator twice
yields byte-identical state.

## Settings block

The `settings` object holds cross-session UI preferences, read/written
through a small typed accessor pair:

```python
def get_setting(self, key, default):
    return self._state.get("settings", {}).get(key, default)

def set_setting(self, key, value) -> None:
    self._state.setdefault("settings", {})[key] = value
    self._save()
```

Currently `settings.size` stores the practice-screen S/M/L text-size preset
(see [tui-screens.md](tui-screens.md#text-size-presets)). Invalid persisted
values are validated by the caller, not the store.

## Free lesson navigation (attemptable vs completion-unlocked)

There are **two** unlock concepts, kept deliberately separate:

```python
def is_unlocked(self, layout_id, unit_index, units) -> bool:
    return True                                          # any lesson attemptable

def is_completion_unlocked(self, layout_id, unit_index, units) -> bool:
    if unit_index == 0:
        return True
    if self.stars_for(layout_id, units[unit_index].id) >= 2:
        return True
    return any(
        self.stars_for(layout_id, units[j].id) >= 2
        for j in range(unit_index + 1, len(units))
    )
```

- **`is_unlocked`** — gates clickability. It is **always True**: every
  lesson, review, and speedtest is attemptable in any order, with no
  previous-unit requirement. The lesson map never disables a row.
- **`is_completion_unlocked`** — drives the **lock badge** (the `🔒` icon)
  and is **derived** from `stars >= 2`:
  - index `0` is always completion-unlocked;
  - a unit with `>= 2` stars is completion-unlocked;
  - the **completion cascade**: if any *later* unit `j > unit_index` has
    `>= 2` stars, every earlier unit is shown completion-unlocked globally
    (completing one lesson retroactively marks all earlier lessons done).

No separate `completed_lessons` list is persisted — completion is derived
from the existing per-unit stars. The lesson-map cursor lands on unit `0`
on mount; `refresh_options()` is called again when a results screen returns
(`results_continue`), so a freshly earned `>= 2` stars immediately lights
up the completion badges of every earlier row.
