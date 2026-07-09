# Overview

tactile is a layered TUI app. The typing domain is pure Python with no I/O;
the Textual UI sits on top and drives it through a small set of `App`
methods. This page maps the modules and the end-to-end data flow.

## Module map

```
src/tactile/
├── __main__.py      CLI: argparse (tactile, practice <path>, --version)
├── app.py           TactileApp: shell, lazy curricula, screen navigation
├── engine.py        TypingSession: pure cursor model, WPM/accuracy, stars
├── curriculum.py    build_curriculum: deterministic, layout-aware units
├── progress.py      ProgressStore: JSON schema, atomic writes, unlocks
├── codeload.py      load_code_exercises: file -> 10-line typing chunks
├── widgets.py       KeyboardWidget + render_stars
├── styles.tcss      Textual CSS
├── layouts/         KeyInfo, Layout, build_char_map, en_us, es_la
├── screens/         layout_select, lesson_map, practice, results, file_picker
└── wordlists/       en.txt, es.txt (bundled, loaded via importlib.resources)
```

## Layering (dependencies point downward only)

```
UI (Textual app + screens + widgets)   app.py, screens/, widgets.py, styles.tcss
        ↓
Progression (JSON persistence)         progress.py
        ↓
Content (layouts + generated units)    curriculum.py, layouts/, wordlists/
        ↓
Engine (pure domain, no I/O)           engine.py
```

The engine and content layers never import Textual or touch the filesystem
(curriculum reads bundled wordlists, but through `importlib.resources`, not
the progress path). This keeps them unit-testable without an event loop.

## End-to-end data flow

```
                     ┌──────────────────┐
                     │  CLI (__main__)  │   tactile | tactile practice <path>
                     └────────┬─────────┘
                              │  TactileApp(progress_path, practice_file?).run()
                              ▼
                     ┌──────────────────┐
   first run ──────► │ LayoutSelectScreen│   OptionList of LAYOUTS names
                     └────────┬─────────┘   on select: store.set_active_layout
                              │             + show_lesson_map(layout_id)
                              ▼
                     ┌──────────────────┐
   returning ──────► │  LessonMapScreen │   curriculum_for(layout_id)
                     │                  │   store.is_unlocked / stars_for / best_wpm_for
                     └────┬────────┬────┘   enter -> open_practice ; p -> file picker
              open unit   │        │  l -> back to layout select
                           ▼        ▼
            ┌──────────────────┐  ┌──────────────────┐
            │  PracticeScreen  │  │ FilePickerScreen │   DirectoryTree over cwd
            │ TypingSession    │  └────────┬─────────┘   on file: open_code_practice
            │  per exercise    │           │
            └────────┬─────────┘◄──────────┘   code: synthetic Unit, record_progress=False
                     │  on exercise done: aggregate (mean acc, mean wpm, min stars)
                     │  store.record(...) or store.record_key_errors(...)
                     ▼
            ┌──────────────────┐
            │  ResultsScreen   │   stars, wpm, accuracy, worst 3 keys
            │  r retry / enter │   r -> results_retry ; enter -> results_continue
            └────────┬─────────┘   results_continue pops 2 screens, refreshes the map
                     │
                     ▼
              (back to LessonMapScreen, next unit now unlocked if >=2 stars)
```

### Key transitions

| From | Event | `App` method | Effect |
|------|-------|--------------|--------|
| Layout select | select option | `show_lesson_map` | sets active layout, pushes map |
| Lesson map | `enter` | `open_practice` | pushes `PracticeScreen` |
| Lesson map | `p` | `show_file_picker` | pushes `FilePickerScreen` |
| Lesson map | `l` | `show_layout_select` | pushes layout select |
| Practice | `escape` | `practice_abort` | pops practice, returns to map |
| Practice | exercise done | `show_results` | pushes `ResultsScreen` |
| Results | `enter` | `results_continue` | pops results + practice, refreshes map |
| Results | `r` | `results_retry` | pops results + practice, reopens practice |

Screens never import each other. They call `self.app.<method>()`, and the
`App` owns the navigation. This is documented further in
[tui-screens.md](tui-screens.md).

## What is lazy

- **Curricula** are built on demand: `curriculum_for(layout_id)` builds and
  caches the `list[Unit]` the first time a layout is opened. Each layout
  gets its own curriculum and its own progress.
- **The `ProgressStore`** loads on construction; if the file is missing or
  corrupt it starts fresh (backing up a corrupt file to `.bak`).

## Where state lives

| State | Owner | Persisted? |
|-------|-------|------------|
| Active layout, per-unit stars/best WPM/best accuracy, key-error heatmap | `ProgressStore` (`~/.tactile/progress.json`) | Yes, atomically |
| Current curriculum(s) | `TactileApp._curricula` | No (rebuilt deterministically) |
| Current unit + exercise index + live `TypingSession` | `PracticeScreen` | No (per run) |

Because the curriculum is deterministic (seeded by
`f"{layout_id}:{unit_index}:{exercise_index}"`), it does not need to be
persisted — rebuilding yields the exact same units. Only the *results* are
stored. See [curriculum.md](curriculum.md) and [progress.md](progress.md).
