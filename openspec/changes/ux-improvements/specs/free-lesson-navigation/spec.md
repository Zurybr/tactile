# Free Lesson Navigation Specification

> New capability (no baseline spec). Drives `progress.py`, `screens/lesson_map.py`,
> `docs/reference/progress-schema.md`. See proposal aspect #4. Curriculum structure
> (units/lessons/reviews/speedtest) is unchanged — only unlock logic + schema.

## Purpose

Lets learners attempt any lesson in any order, and records completion (>= 2 stars)
so all earlier lessons across ALL units are reflected as unlocked. Adds a forward-
only, idempotent v1 -> v2 schema migration that preserves all existing bests.

## Requirements

### Requirement: Any Lesson Attemptable

`ProgressStore.is_unlocked` MUST return True for every unit regardless of prior
progress. No lesson, review, or speedtest is gated by a previous unit's stars.

#### Scenario: First lesson is attemptable (unchanged)

- GIVEN a fresh store and the curriculum's first unit
- WHEN is_unlocked is queried
- THEN it returns True

#### Scenario: Later lesson attemptable without prior progress

- GIVEN a fresh store and the curriculum's 10th unit (or any non-first unit)
- WHEN is_unlocked is queried
- THEN it returns True (no previous-unit >= 2 stars requirement)

### Requirement: Completion Unlocks All Previous Lessons Globally

Completing ANY lesson with >= 2 stars MUST mark every lesson with a lower index
across ALL units as unlocked in the persisted/displayed state. Below 2 stars MUST
NOT trigger the completion-based unlock. Completion state is DERIVED from
`stars >= 2` (no separate `completed_lessons` list is required by this spec).

#### Scenario: Completing a later lesson marks earlier ones unlocked

- GIVEN a fresh store and the lesson map reflecting locked/unlocked display
- WHEN the user completes unit index 5 with 2 stars
- THEN every lesson with index < 5 across all units is displayed as unlocked

#### Scenario: Below two stars does not change unlock display

- GIVEN a fresh store
- WHEN the user completes a lesson with 1 star
- THEN no completion-based unlock display change is applied

### Requirement: Schema v2 with Settings Block

The progress JSON schema MUST move `version` from 1 to 2 by adding a top-level
`settings` object (default `{}`). Existing v1 fields (`version`, `active_layout`,
`layouts` -> per-layout `lessons` / `key_errors`) MUST be preserved verbatim.

#### Scenario: v2 default state includes settings

- GIVEN a brand-new progress store
- WHEN it is saved
- THEN the JSON contains `"version": 2` and `"settings": {}`

#### Scenario: Existing per-lesson bests shape is unchanged

- GIVEN a v2 store with a recorded lesson
- WHEN it is saved
- THEN the lesson entry still has stars / best_wpm / best_acc
- AND key_errors still accumulates per layout

### Requirement: Idempotent v1 -> v2 Migration

On load, if the file `version` is missing or equals 1, the store MUST run a
forward-only migrator that (a) sets `version` to 2, (b) adds `settings` if absent,
and (c) preserves all existing stars, best_wpm, best_acc, and key_errors
unchanged. The migrator MUST be idempotent: running it twice yields identical state.
The v1 file MUST be backed up to `.bak` before the first v2 write. A v1 file MUST
NOT be treated as corrupt.

#### Scenario: v1 file migrates to v2 preserving stars

- GIVEN a v1 progress file with a lesson stars = 4 and key_errors {"f": 12}
- WHEN the store loads
- THEN version becomes 2, settings is present, stars remain 4, key_errors remain {"f": 12}

#### Scenario: Migration is idempotent

- GIVEN an already-migrated v2 file
- WHEN the migrator runs again
- THEN the state is unchanged (version 2, same settings, same stars, same bests)

#### Scenario: Round-trip preserves state

- GIVEN a v2 store with stars, best_wpm, and a non-empty settings block
- WHEN it is saved and reloaded
- THEN every field equals the original

### Requirement: Tests for Migration and Unlock

`tests/test_progress.py` MUST cover: v1 -> v2 migration preserving stars and
key_errors, idempotent re-migration, v2 round-trip, any-lesson-attemptable, and the
>= 2 stars global unlock display. The existing corrupt-file backup behavior MUST
remain for truly corrupt (unparseable / wrong-type) files.

#### Scenario: Corrupt file still backed up

- GIVEN a progress file that is unparseable JSON
- WHEN the store loads
- THEN the file is renamed to `.bak` and a fresh v2 store starts (does NOT go through v1 migration)
