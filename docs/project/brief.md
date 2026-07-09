# Brief

tactile is a terminal touch-typing trainer. It teaches touch typing through
progressive lessons that introduce keys outward from the home row, gives live
feedback, and rates each unit with stars — all inside the terminal.

## The problem

Most touch-typing trainers are web apps. For developers who live in the
terminal, that means context-switching to a browser, an account, and a
stream of ads. tactile keeps the practice where the work happens: in the
terminal, offline, with no account and no network.

It also targets a gap that few trainers cover well: the **Latin American
Spanish keyboard layout**. Keys like `ñ`, dead-key accents (`á é í ó ú ü`),
and AltGr symbols (`@` via `AltGr+Q`) are first-class, with a curriculum
generated for that layout rather than translated from English.

## Target audience

- Developers and power users who work in the terminal daily.
- Learners on either an English (US) or Español (Latinoamérica) layout.
- Anyone who wants to practice typing their own code or prose, not canned
  sentences.

## Scope (v1)

What tactile does in 0.1.0:

- **Progressive curriculum** generated per layout from home row outward.
  A review unit every 5th lesson and a final speed test.
- **Live WPM and accuracy** updated while typing, plus an on-screen keyboard
  that highlights the next key and shows the finger + modifier to use.
- **1-5 star rating** per unit, with sequential unlocking at >=2 stars.
- **Two layouts**: English (US) and Español (Latinoamérica), each with its
  own curriculum and its own progress.
- **Code/text file practice**: any file becomes typing exercises, chunked
  into 10-line segments.
- **Resilient progress** stored as schema-versioned JSON, written atomically,
  with a `.bak` backup on corruption.

## Non-goals (v1)

Explicitly out of scope for the first release:

- Multiple user profiles or cloud sync.
- A custom lesson authoring UI.
- Sound effects.
- Detailed per-finger analytics dashboards.
- Non-QWERTY layouts (Dvorak, Colemak, etc.).
- Localization of the UI copy (the UI is English; curriculum unit titles for
  the Spanish layout are Spanish because they are *content* for Spanish-layout
  learners).

## How it fits together

The project is layered so the typing domain has no dependency on the UI:

```
UI (Textual app + screens)   -> progression -> content -> engine (pure)
```

See [engineering/overview.md](../engineering/overview.md) for the full
end-to-end data flow, and [project/textual.md](textual.md) for why Textual
was chosen.
