# Textual

tactile's UI is built with [Textual](https://textual.textualize.io/)
(`textual>=0.60`, the single runtime dependency). Textual is a TUI framework
built on top of Rich that lets you compose screens and widgets much like a
web framework, with CSS-like styling and async event handling.

## Why Textual

| Need | Textual |
|------|---------|
| Layout, focus, and screen navigation in the terminal | First-class `App`, `Screen`, widget composition, `push_screen`/`pop_screen` |
| Styling without hand-rolling rendering | A `.tcss` CSS file (`CSS_PATH`) |
| Testable UI without a real terminal | The `Pilot` API drives the app headlessly in pytest |
| Rich text rendering (colours, reverse video) | Built on Rich, so `rich.text.Text` works directly |
| Active maintenance and Python 3.12+ support | Yes |

### Alternatives considered (and rejected)

These were evaluated during the original design (see
[decisions](../decisions/README.md)):

- **prompt_toolkit** — capable, but lower-level. It gives you a rendering
  abstraction rather than a screen/widget/compose model, so building the
  lesson map, practice loop, and keyboard widget would mean re-implementing
  much of what Textual provides.
- **curses** — the standard-library option, but it is platform-quirky
  (especially on Windows, the primary target), unstyled by default, and
  has no built-in testing story. The amount of plumbing for layout, focus,
  and colour would dwarf the typing logic.
- **rich** alone — Rich is excellent for *output*, but it is not an
  application framework. Textual already uses Rich internally; reaching for
  raw Rich would mean losing screen management, event handling, and Pilot
  tests. (tactile does use `rich.text.Text` directly for styled spans in
  `widgets.py` and `screens/practice.py`, which is fine — that is a Rich
  *type*, not a replacement framework.)

## Patterns used

- **`App` subclass** — `TactileApp(App)` is the shell. It owns the
  `ProgressStore`, lazily builds per-layout curricula, and exposes
  navigation methods (`show_lesson_map`, `open_practice`, `show_results`,
  …) that screens call via `self.app.<method>()`.
- **Screens** — one `Screen` per role: `LayoutSelectScreen`,
  `LessonMapScreen`, `PracticeScreen`, `ResultsScreen`, `FilePickerScreen`.
  Screens never import each other; transitions go through `App` methods
  (documented in [engineering/tui-screens.md](../engineering/tui-screens.md)).
- **`compose()`** — each screen yields its widgets (`Header`, `OptionList`,
  `Static`, `KeyboardWidget`, `Footer`). Styling comes from
  [`styles.tcss`](../../src/tactile/styles.tcss) plus design-system tokens
  (`$surface`, `$primary`, `$text-muted`).
- **Bindings** — `BINDINGS` on each `Screen` expose keys to the `Footer`
  (`q`, `l`, `p`, `escape`, `r`, `enter`).
- **`Pilot` tests** — async tests run the app headlessly with
  `async with app.run_test() as pilot:` and drive it with
  `pilot.press(...)` / `pilot.pause()`. See
  [engineering/testing.md](../engineering/testing.md).

## Gotchas encountered

### `Widget.layout` is a reserved property

Textual's `Widget` declares `layout` as a read-only property (it is the
layout engine). The planned constructor signature for `PracticeScreen` and
`KeyboardWidget` takes a keyboard `layout: Layout` argument, so the value
is stored under a different attribute name instead:

```python
# widgets.py / screens/practice.py
def __init__(self, layout: Layout, **kwargs) -> None:
    super().__init__(**kwargs)
    # `layout` is a reserved Textual Widget property, so the
    # keyboard layout is stored under a different attribute name.
    self.keyboard_layout = layout
```

This deviation is noted in the implementation plan (Task 7).

### Space is pressed as `"space"` in Pilot

In a `Pilot` test, the space character is pressed with `pilot.press("space")`,
not `pilot.press(" ")`. Code that maps exercise text to key presses must
convert `" "` → `"space"` (and `"\n"` → `"enter"`).

### `event.stop()` while typing

`PracticeScreen.on_key` calls `event.stop()` after handling a printable key
so that screen bindings do not fire mid-typing, while still letting
`escape` reach its binding.

## Where Textual appears in the code

| File | Role |
|------|------|
| `app.py` | `TactileApp(App)`: shell, `CSS_PATH`, navigation methods |
| `screens/*.py` | one `Screen` subclass per role |
| `widgets.py` | `KeyboardWidget(Static)` + `render_stars` |
| `styles.tcss` | app-wide styling |

The pure-logic modules (`engine`, `curriculum`, `progress`, `codeload`,
`layouts`) deliberately **do not** import Textual, so they stay unit-testable
without an event loop.
