# TUI & Screens

The UI is a `TactileApp(App)` shell that pushes and pops `Screen` objects.
Each screen owns one role; the `App` owns navigation. This page documents
the shell, the screens, the navigation pattern, and the widgets.

## `TactileApp` — the shell

```python
class TactileApp(App):
    CSS_PATH = "styles.tcss"
    TITLE = "tactile"

    def __init__(self, progress_path=None, practice_file=None): ...
```

The shell owns three things:

- **`self.store`** — a `ProgressStore(progress_path)` (the progress file is
  injectable for tests).
- **`self._curricula`** — a lazy cache of per-layout `list[Unit]`, built by
  `curriculum_for(layout_id)` on first access.
- **`self.current_unit`** — the unit being practiced (exposed for tests).

### `on_mount` routing

```python
def on_mount(self) -> None:
    if self.practice_file is not None:
        layout_id = self.store.active_layout or "en_us"
        self.show_lesson_map(layout_id)
        self.open_code_practice(self.practice_file)
    elif self.store.active_layout is None:
        self.show_layout_select()
    else:
        self.show_lesson_map(self.store.active_layout)
```

Three entry points: `tactile practice <path>` lands straight in code practice
(over the active layout, or `en_us` fallback); a first run with no active
layout shows layout select; a returning user goes straight to the lesson map.

## Navigation pattern (important)

**Screens never import each other.** Every transition goes through an `App`
method, called from a screen via `self.app.<method>()`:

```python
# in a screen
def on_option_list_option_selected(self, event):
    self.app.open_practice(self.layout_id, unit)   # type: ignore[attr-defined]
```

This keeps the screens decoupled and the navigation logic in one place.
The `type: ignore[attr-defined]` comments acknowledge that `self.app` is
typed as the base `App`, which does not declare these methods.

The full transition table is in [overview.md](overview.md#key-transitions).

## The screens

### `LayoutSelectScreen`

An `OptionList` of `LAYOUTS[...].name` values. Selecting one calls
`store.set_active_layout(layout_id)` and `app.show_lesson_map(layout_id)`.
The first option is highlighted on mount. Reachable on first run and later
via the `l` key from the lesson map.

### `LessonMapScreen`

A scrollable `OptionList` of a layout's units. Each row shows:

```
<lock> <stars>  <unit title>  (<best wpm> wpm)
```

- **lock** — a space if completion-unlocked, `🔒` if completion-locked.
  Driven by `store.is_completion_unlocked(...)` (derived from `>= 2` stars),
  **not** by clickability.
- **stars** — `render_stars(stars)` (5 slots, `★`/`☆`).
- **best wpm** — `best_wpm_for(...)`, or `--- wpm` when unseen.

Every row is **clickable** — free navigation means `is_unlocked` is always
`True`, so no row is ever disabled. The lock is a display badge only.

`refresh_options()` rebuilds the list and lands the cursor on unit `0`. It
is called on mount and again when a results screen returns
(`results_continue`), so a freshly earned `>= 2` stars immediately lights up
the completion badges of every earlier row (the completion cascade).

Bindings: `q` quit, `l` change layout, `p` practice a file. `enter` opens
the highlighted unit via `app.open_practice`.

### `PracticeScreen` — the core loop

Runs a unit's exercises one at a time through a `TypingSession`. Composes:

```
Static#practice-title     "Unit title - exercise i/n"
Static#practice-stats     "WPM  32.5   ACC  97.2%"   (refreshed every 0.5s)
Static#practice-text      target with green/reverse/dim spans
KeyboardWidget            on-screen keyboard + finger/modifier hint
Footer
```

- A `set_interval(0.5, _update_stats)` ticks the live WPM/accuracy line
  while typing; it is stopped when the unit finishes.
- `on_key` handles `enter` → `session.on_key("\n")`, `backspace` →
  `on_backspace()`, and printable chars → `on_key(character)`. Each handled
  key calls `event.stop()` so bindings do not fire mid-typing; `escape` is
  let through to its binding.
- The cursor char is rendered reversed; it turns `reverse red` right after a
  wrong attempt. A `\n` cursor renders as `⏎`.
- On exercise completion: if more exercises remain, advance within the unit
  (per-exercise stats reset). After the last exercise: aggregate the unit
  (mean accuracy, mean WPM, **min** stars), record to the store, and push
  `ResultsScreen`.

The `keyboard_layout` is stored as `self.keyboard_layout`, **not**
`self.layout`, because `layout` is a reserved `Widget` property (see
[project/textual.md](../project/textual.md#widgetlayout-is-a-reserved-property)).

### `ResultsScreen`

Shows the aggregate unit result: title, `render_stars`, WPM, accuracy, and
the top-3 worst keys (`'f' x12`). If there were no errors, it prints
"No errors - flawless run!". Bindings: `r` retry, `enter` back to map.

### `FilePickerScreen`

A `DirectoryTree` over the current working directory. Selecting a file
pops the picker and calls `app.open_code_practice(path)`. `escape` cancels.

## `App` navigation methods

| Method | Effect |
|--------|--------|
| `show_layout_select` | push `LayoutSelectScreen` |
| `show_lesson_map(layout_id)` | push `LessonMapScreen` |
| `show_file_picker` | push `FilePickerScreen` |
| `open_practice(layout_id, unit, record_progress=True)` | push `PracticeScreen` |
| `open_code_practice(path)` | build a synthetic `Unit`, push practice with `record_progress=False` |
| `show_results(...)` | push `ResultsScreen` |
| `practice_abort` | pop `PracticeScreen` (back to map) |
| `results_continue` | pop results + practice, then `refresh_options` on the map |
| `results_retry(layout_id, unit, record_progress)` | pop results + practice, reopen practice |

### Code practice synthetic unit

`open_code_practice` builds a throwaway unit so code practice reuses the
practice screen:

```python
unit = Unit(
    id=f"code:{path.name}",
    title=f"Code practice: {path.name}",
    kind="lesson",
    new_chars="",
    wpm_target=30.0,
    exercises=tuple(exercises),
)
self.open_practice(layout_id, unit, record_progress=False)
```

Because `record_progress=False`, results are shown but only the key-error
heatmap is recorded (see [progress.md](progress.md#record_key_errors-code-practice)).

## Widgets

### `render_stars(stars)`

```python
def render_stars(stars: int) -> str:
    return "★" * stars + "☆" * (5 - stars)   # 5 slots, e.g. 3 -> "★★★☆☆"
```

Used by the lesson map rows and the results screen.

### `KeyboardWidget(Static)`

Renders `layout.rows` as staggered key caps (each row indented by its index,
mimicking physical keyboard stagger) and highlights the next expected key:

- `highlight(char)` re-renders with the cap for `char_map[char]` shown in
  `bold reverse`, plus a hint line.
- The hint combines the **finger** and the **modifier**:
  - `none` → `"<finger>"` (e.g. `"left index"`)
  - `shift` → `"<finger> - Shift + <cap>"`
  - `altgr` → `"<finger> - AltGr + <cap>"`
  - `dead` → `"<finger> - <hint>"` (e.g. `"left pinky - ´ then a"`)
- Space → `"thumb - Space"`; `\n` → `"right pinky - Enter"`; an untypable
  char → `"not on this layout: <char>"`.

The widget also stores its layout as `self.keyboard_layout` for the same
reserved-property reason as `PracticeScreen`.

## Styling

[`styles.tcss`](../../src/tactile/styles.tcss) is small and uses Textual's
design-system tokens: screens are centred on `$surface`; `OptionList`s and
the results body get a `round $primary` border; the practice stats line is
`$text-muted`. There is no per-widget colour hardcoding — theming comes from
the tokens.

### Centered practice-screen layout

Every practice-screen element — `#practice-title`, `#practice-stats`,
`#practice-text`, and `#practice-keyboard` — resolves to `text-align: center`
inside its `90%` container, while the containers themselves stay centred on
screen via the existing `Screen { align: center middle }`. The results body
(`#results-body`) was already centred and remains so.

```css
#practice-title, #practice-stats, #practice-text, #practice-keyboard {
    text-align: center;
}
```

`tests/test_centered_layout.py` asserts each widget's resolved `text_align`
equals `"center"` through the real Textual CSS cascade, so a CSS revert
(left-align) fails the test.

#### Ergonomics note (cursor anchor shift)

Centering multi-line practice text shifts the cursor's **anchor column** on
every line of a multi-line target: a short line centres within the container,
so the column where the next character lands differs from the line above.
Touch-typists who practise to a steady **left-rhythm** may find this slightly
disorienting on multi-line exercises (and on code practice). Single-line
drills are unaffected because each drill is one line.

This is an accepted trade-off of the centred layout for visual consistency.
A future iteration **may** add an escape hatch (e.g. a CSS class that
re-applies `text-align: left` to `#practice-text` only) to restore the
left-anchored rhythm without un-centring the rest of the screen. That escape
hatch is **not** in scope for this change.
