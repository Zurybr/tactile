# Keybinds

In-app keybindings, grouped by screen. Bindings are declared on each `Screen`
via `BINDINGS` and shown in the Textual `Footer`.

| Key | Screen | Action | Binding source |
|-----|--------|--------|----------------|
| `enter` | Layout select | Pick the highlighted layout; set it active and go to its lesson map. | `OptionList.OptionSelected` handler |
| `enter` | Lesson map | Open the highlighted unit in `PracticeScreen`. | `OptionList.OptionSelected` handler |
| `enter` | Results | Return to the lesson map (refreshes lock/star state). | `Binding("enter", "continue", "Back to map")` |
| `escape` | Practice | Abort the run and return to the lesson map. Nothing is recorded. | `Binding("escape", "back_to_map", "Back to map")` |
| `escape` | File picker | Cancel and return to the lesson map. | `Binding("escape", "cancel", "Back to map")` |
| `+` | Practice | Cycle the text-size preset up (S -> M -> L -> S). Changes container width + text weight, not glyph pixels; use the terminal emulator's zoom (Ctrl++ / Ctrl+-) for true zoom. | `Binding("plus", "cycle_size_up", "Size +")` |
| `-` | Practice | Cycle the text-size preset down (S -> L -> M -> S). Same width + weight semantics as `+`. | `Binding("minus", "cycle_size_down", "Size -")` |
| `r` | Results | Retry the same unit from exercise 1. | `Binding("r", "retry", "Retry unit")` |
| `p` | Lesson map | Open the file picker (`DirectoryTree` over the cwd) for code practice. | `Binding("p", "practice_file", "Practice a file")` |
| `l` | Lesson map | Change keyboard layout (pushes the layout select screen). | `Binding("l", "change_layout", "Change layout")` |
| `q` | Lesson map | Quit tactile. | `Binding("q", "quit", "Quit")` |

## Typing keys (Practice screen)

While in `PracticeScreen`, printable characters are sent to the
`TypingSession`:

| Key | Engine call | Effect |
|-----|-------------|--------|
| printable char | `session.on_key(char)` | Advance if correct; otherwise record an error and stay. |
| `enter` | `session.on_key("\n")` | Satisfy a `\n` in the target (code practice / multi-line). |
| `backspace` | `session.on_backspace()` | Step back one position if possible. Does not erase recorded errors. |

Every handled typing key calls `event.stop()` so that screen bindings do not
fire mid-typing. `escape` is intentionally let through to its binding so you
can leave practice at any time.

## Where to look in the code

| Screen | File |
|--------|------|
| Layout select | `src/tactile/screens/layout_select.py` |
| Lesson map | `src/tactile/screens/lesson_map.py` |
| Practice | `src/tactile/screens/practice.py` |
| Results | `src/tactile/screens/results.py` |
| File picker | `src/tactile/screens/file_picker.py` |
