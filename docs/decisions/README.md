# Decisions

Historical design artifacts for the `tactile` project, kept as a lightweight
architecture decision record. These documents capture the thinking at the time
each change was specified and planned; they are **frozen snapshots**, not living
documentation, so they may reference names or structure that have since changed
(notably the earlier `touchtype` package name, and a `~/.touchtype/` progress
path that became `~/.tactile/`). Source code is the source of truth for the
current state.

The artifacts come from the SDD (Spec-Driven Development) process and are split
into two folders:

- **`specs/`** - requirements and scenarios for a change (the "what" and "why").
- **`plans/`** - implementation task breakdowns for a change (the "how" and
  "when").

## Index

### Specs

- [`specs/2026-07-08-touchtype-tui-design.md`](specs/2026-07-08-touchtype-tui-design.md)
  - Original TUI design spec: Textual app shell, screens, curriculum engine,
    progress store, and keyboard layout data. See the current implementation in
    [[engineering/overview|Overview]], [[engineering/engine|Engine]],
    [[engineering/curriculum|Curriculum]], [[engineering/progress|Progress]],
    and [[engineering/tui-screens|TUI & Screens]].

### Plans

- [`plans/2026-07-08-touchtype-tui.md`](plans/2026-07-08-touchtype-tui.md)
  - Implementation plan that broke the original TUI build into sequenced tasks.
    The strict-TDD workflow it mandates is documented in
    [[engineering/testing|Testing]] and [[project/pytest|pytest]]; the layout
    data it specifies lives in [[engineering/layouts|Layouts]].

## How these records relate to the code

These files are frozen at their original dates. Where a past decision has a
current implementation page, the wikilinks above point to it. Notable
evolutions since the original spec/plan:

- **Package name** `touchtype` → `tactile` (the rename is committed).
- **Progress path** `~/.touchtype/progress.json` → `~/.tactile/progress.json`.
- **Python version** the spec mentions 3.14; the shipped requirement in
  `pyproject.toml` is `>=3.12` (the source of truth).
- **`{`/`}` on es_la** the plan's first draft assumed AltGr; the implementation
  corrected this to the unshifted base chars per the real KBDLA layout (see
  [[engineering/layouts#the-brace-deviation|Layouts § the brace deviation]]).

## Conventions

- Filenames are dated `YYYY-MM-DD-<slug>.md`.
- New SDD changes add a new dated spec under `specs/` and (when planned) a
  matching plan under `plans/`; existing files are not edited after the fact.
