# Text Size Control Specification

> New capability (no baseline spec in `openspec/specs/`). Drives `styles.tcss`,
> `screens/practice.py`, `progress.py`, `app.py`. See proposal aspect #1.

## Purpose

A user-controlled "text size" preference (S/M/L) that adjusts the visual prominence
of practice-screen content by combining container width and text weight. It does NOT
resize glyph pixels — terminals cannot do that. The setting persists across sessions.

## Requirements

### Requirement: Three Size Presets

The system MUST expose exactly three presets: Small (S), Medium (M, default), Large
(L). Each preset MUST adjust BOTH (a) the practice container width and (b) the text
weight: L = bold, M = normal, S = light/dim. The system MUST NOT promise or implement
pixel-level glyph scaling. Cycling via `+` / `-` MUST wrap (S -> M -> L -> S).

#### Scenario: Medium is the default on first launch

- GIVEN a fresh progress store with no saved size setting
- WHEN the practice screen loads
- THEN the active preset is M (normal weight, default width)

#### Scenario: Plus key cycles Medium to Large

- GIVEN the practice screen is showing with preset M
- WHEN the user presses the `+` key
- THEN the preset becomes L
- AND the practice container widens and text weight becomes bold

#### Scenario: Minus key cycles downward L -> M -> S

- GIVEN the practice screen is showing with preset L
- WHEN the user presses the `-` key twice
- THEN the preset becomes M then S
- AND at S the container narrows and text weight becomes light/dim

#### Scenario: Cycling wraps at both ends

- GIVEN the preset is S
- WHEN the user presses `-`
- THEN the preset wraps to L
- AND given the preset is L, pressing `+` wraps to S

### Requirement: Persistence Across Sessions

The active size preset MUST be stored in the progress JSON `settings` block and
restored on the next app launch via `ProgressStore`.

#### Scenario: Setting survives restart

- GIVEN the user set the size to L during a session
- WHEN the app is closed and reopened
- THEN the practice screen loads with preset L

#### Scenario: Persisted value is respected even if invalid

- GIVEN a stored `settings.size` value outside {S, M, L}
- WHEN the store loads
- THEN the preset falls back to M (default) without crashing

### Requirement: Terminal Zoom Constraint Documentation

The system MUST document — in the in-app help/keybinds reference AND in
`docs/engineering/tui-screens.md` — that "text size" adjusts width + weight only,
and that true zoom is the terminal emulator's job (Ctrl++ / Ctrl+-). The docs MUST
NOT claim pixel scaling.

#### Scenario: Help text states the constraint

- GIVEN a user opens the help / keybinds reference
- THEN the text states that presets change width + weight, not glyph pixels
- AND points the user to the terminal emulator's zoom controls
