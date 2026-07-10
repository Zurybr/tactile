# Forgiving Error Model Specification

> New capability (no baseline spec). REPLACES the edclub "hold-cursor" model in
> `engine.py`. Highest-risk capability — precision is mandatory. Drives
> `engine.py`, `tests/test_engine.py`, `docs/engineering/engine.md`. See proposal
> aspect #3.

## Purpose

Wrong keys now ADVANCE the cursor (the learner types past mistakes); backspace
ERASES recorded errors so a position can be re-evaluated; scoring awards partial
credit (0.5) for positions errored then later corrected. This is a REPLACEMENT —
the old hold-cursor model is removed, not opted into.

## Requirements

### Requirement: Wrong Key Advances Cursor and Records Error

When the typed char does not match the expected char, the engine MUST (a) record an
error at the current position in `error_positions`, (b) record the expected char in
`key_errors`, AND (c) advance the cursor by one. The engine MUST NOT hold the cursor
on a wrong key.

#### Scenario: Wrong key advances and records

- GIVEN a TypingSession on target "cat" at position 0 (expected 'c')
- WHEN the user types 'x'
- THEN position becomes 1
- AND error_positions records position 0
- AND key_errors records 'c'

#### Scenario: Typing past errors reaches completion

- GIVEN a TypingSession on target "hi"
- WHEN the user types 'x' then 'y'
- THEN position is 2 and is_complete is True
- AND error_positions records both position 0 and 1

### Requirement: Backspace Erases Recorded Errors

When the cursor steps back over a position that has a recorded error, the engine
MUST remove that position's entry from `error_positions`, making the position
eligible for re-evaluation when retyped. The engine MUST decrement position when
`position > 0`.

#### Scenario: Backspace over an error clears it

- GIVEN a session where position 0 was typed wrong (error recorded, cursor at 1)
- WHEN the user presses backspace
- THEN position returns to 0
- AND error_positions no longer contains position 0

#### Scenario: Backspace over a first-try-correct position

- GIVEN a session where position 0 was typed correctly on the first try (cursor at 1)
- WHEN the user presses backspace
- THEN position returns to 0
- AND no error entry exists for position 0

### Requirement: Correction Partial Credit (0.5 Weight)

The engine MUST distinguish three position outcomes: first-try-correct (weight 1.0),
corrected (errored then later typed correctly after a backspace, weight 0.5), and
uncorrected (still errored at completion, weight 0.0). Typing the correct key at a
backspaced-to error position MUST mark that position as corrected, not first-try.

#### Scenario: Correcting an error yields partial credit

- GIVEN a session where position 0 was errored, then backspaced clear
- WHEN the user types the correct char at position 0
- THEN position 0 is recorded as corrected with weight 0.5 (not first-try-correct)

#### Scenario: Never-corrected error yields no credit

- GIVEN a completed session where position 0 was wrong and never revisited
- THEN position 0 contributes 0.0 credit

### Requirement: Accuracy Formula (Weighted Positions)

`accuracy` MUST equal `(credited / total_positions) * 100`, where:

- `credited = first_try_correct * 1.0 + corrected * 0.5 + uncorrected * 0.0`
- **Live display** (during the exercise, `is_complete is False`): `total_positions = max(position, 1)` — reflects only characters attempted so far, so the display shows real performance (e.g., 100% if perfect so far).
- **Final accuracy** (at completion, `is_complete is True`): `total_positions = len(target)` — the full exercise length.
- An empty/untouched session MUST return 100.0 (no keystrokes).

A perfect run (all first-try-correct) MUST yield 100.0.

#### Scenario: All first-try-correct is 100%

- GIVEN a completed session on "cat" typed correctly first try throughout
- THEN accuracy is 100.0

#### Scenario: One corrected error in a 4-char target

- GIVEN a completed session on "abcd" where position 0 was errored, backspaced, and retyped correctly; positions 1-3 first-try-correct
- THEN credited = 0.5 + 1 + 1 + 1 = 3.5; total = 4; accuracy = 87.5

#### Scenario: One uncorrected error in a 4-char target

- GIVEN a completed session on "abcd" where position 0 was wrong and never corrected; positions 1-3 first-try-correct
- THEN credited = 0 + 1 + 1 + 1 = 3.0; accuracy = 75.0

#### Scenario: Live accuracy uses attempted-so-far denominator

- GIVEN a session on "abcdef" (6 chars) where the user has typed 3 chars perfectly (position 3, is_complete False)
- THEN live accuracy = 3.0 / 3 * 100 = 100.0 (NOT 3.0 / 6 * 100 = 50.0)
- WHEN the user completes all 6 chars perfectly
- THEN final accuracy = 6.0 / 6 * 100 = 100.0

### Requirement: Net WPM Uses Credited Chars

`net_wpm` MUST be computed from credited chars: `((first_try_correct + corrected *
0.5) / 5) / minutes`. `gross_wpm` continues to use total keystrokes. Both MUST
return 0.0 before the timer starts.

#### Scenario: Net WPM reflects credited chars

- GIVEN a completed session with 5 first-try-correct and 1 corrected (0.5 credit) over exactly 1 minute
- THEN net_wpm = (5.5 / 5) / 1 = 1.1

### Requirement: Stars Use New Accuracy (Same Thresholds)

`stars(wpm_target)` MUST apply the existing ladder
`_STAR_ACCURACY_THRESHOLDS = (90.0, 95.0, 97.0, 99.0)` against the NEW accuracy and
net_wpm. The cascade error -> accuracy -> net_wpm -> stars MUST be internally
consistent: the same `accuracy`/`net_wpm` feed both stars and record.

#### Scenario: Stars ladder boundaries hold with new accuracy

- GIVEN completed sessions with accuracies 89.9, 90.0, 95.0, 97.0 (wpm >= target), 99.0 (wpm >= target)
- THEN stars are 1, 2, 3, 4, 5 respectively

### Requirement: Record Persists New Bests

`ProgressStore.record` MUST continue to store max-best stars / best_wpm / best_acc
using the new accuracy and net_wpm. The formula change MUST NOT alter the
max-preservation or key_errors accumulation contract.

#### Scenario: Best accuracy tracks new formula

- GIVEN a stored best_acc of 90.0 and a replay scoring 87.5 (new accuracy)
- THEN best_acc remains 90.0 (max preserved)

### Requirement: Old Hold-Cursor Model Removed

The engine MUST NOT retain a hold-cursor code path or an opt-in toggle. The
forgiving model is the only model. All ~13 existing engine tests MUST be rewritten
(red -> green) to reflect advances-on-error, backspace-erases, and weighted
accuracy. New tests MUST cover: correction partial credit, backspace erasure,
cursor-advance-on-error, and each accuracy-formula case above.

#### Scenario: Engine test suite reflects the new model

- GIVEN the rewritten tests/test_engine.py
- WHEN `uv run python -m pytest -q tests/test_engine.py` runs
- THEN all tests pass
- AND no test asserts hold-cursor or permanent-error behavior
