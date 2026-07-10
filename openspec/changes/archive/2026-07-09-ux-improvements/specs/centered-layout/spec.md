# Centered Layout Specification

> New capability (no baseline spec). Drives `styles.tcss`, `widgets.py`. See
> proposal aspect #2. Pure CSS + visual verification; no domain logic change.

## Purpose

All on-screen UI elements — title, stats, practice text, and keyboard — render
centered within their containers, producing a visually consistent screen. Today
only `#results-body` is centered; everything else is left-aligned within a 90%
container.

## Requirements

### Requirement: Center All Practice-Screen Elements

The system MUST center the text content of `#practice-title`, `#practice-stats`,
`#practice-text`, and `#practice-keyboard` (`text-align: center`). The containers
themselves MUST remain centered on screen via the existing `Screen { align: center
middle }`.

#### Scenario: Practice text is centered

- GIVEN the practice screen showing a multi-line target string
- WHEN a Textual Pilot snapshot is captured
- THEN each line of the target text is centered within the practice container
- AND the snapshot matches the committed baseline

#### Scenario: Title and stats are centered

- GIVEN the practice screen is visible
- WHEN a Pilot snapshot is captured
- THEN the title and stats line render centered, not left-aligned

#### Scenario: Keyboard stagger remains visually centered

- GIVEN the keyboard widget renders its per-row stagger indent (`" " * row_index`)
- WHEN a Pilot snapshot is captured
- THEN the keyboard block reads as centered with no lateral drift
- AND the committed baseline snapshot matches

### Requirement: Results Screen Stays Centered

`#results-body` is already centered and MUST remain so. No regression allowed.

#### Scenario: Results screen unchanged

- GIVEN a completed exercise shows the results screen
- THEN the results body remains centered exactly as before this change

### Requirement: Pilot Snapshot Verification

The implementation MUST include a Pilot-driven snapshot/visual test that confirms
centering of title, stats, practice text, and keyboard. Any centering regression
MUST fail this test.

#### Scenario: Centering regression is caught

- GIVEN the centered layout is implemented and the snapshot test is green
- WHEN any element's `text-align` is reverted to left
- THEN the Pilot snapshot test fails

### Requirement: Ergonomics Note and Future Escape Hatch

The change SHOULD document in `docs/engineering/tui-screens.md` the ergonomic risk
that centering multi-line practice text shifts the cursor's anchor column per line,
which may break the left-rhythm touch-typists expect. The change MAY leave a
documented escape hatch (e.g. a CSS class to revert `#practice-text` to left-align)
for a future iteration, but building that escape hatch is NOT in this change's scope.

#### Scenario: Risk documented

- GIVEN the centered-layout change is delivered
- THEN `docs/engineering/tui-screens.md` records the ergonomics risk and the possible future escape hatch
