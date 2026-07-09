# Decisions

Historical design artifacts for the `tactile` project, kept as a lightweight
architecture decision record. These documents capture the thinking at the time
each change was specified and planned; they are **frozen snapshots**, not living
documentation, so they may reference names or structure that have since changed
(notably the earlier `touchtype` package name). Source code is the source of
truth for the current state.

The artifacts come from the SDD (Spec-Driven Development) process and are split
into two folders:

- **`specs/`** - requirements and scenarios for a change (the "what" and "why").
- **`plans/`** - implementation task breakdowns for a change (the "how" and
  "when").

## Index

### Specs

- [`specs/2026-07-08-touchtype-tui-design.md`](specs/2026-07-08-touchtype-tui-design.md)
  - Original TUI design spec: Textual app shell, screens, curriculum engine,
    progress store, and keyboard layout data.

### Plans

- [`plans/2026-07-08-touchtype-tui.md`](plans/2026-07-08-touchtype-tui.md)
  - Implementation plan that broke the original TUI build into sequenced tasks.

## Conventions

- Filenames are dated `YYYY-MM-DD-<slug>.md`.
- New SDD changes add a new dated spec under `specs/` and (when planned) a
  matching plan under `plans/`; existing files are not edited after the fact.
