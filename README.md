# tactile

A terminal touch-typing trainer built with [Textual](https://textual.textualize.io/).
Progressive lessons introduce keys outward from the home row (edclub style),
with live WPM/accuracy, a 1-5 star rating per unit, sequential unlocking, and
an on-screen keyboard with finger hints. It also turns any code or text file
into typing practice.

## Layouts

Two keyboard layouts are included, selectable at startup and switchable later
with the `l` key: **English (US)** and **Español (Latinoamérica)** (home row
with ñ, dead-key accents, AltGr symbols). Each layout gets its own generated
curriculum and its own progress.

## Install

Requires Python >= 3.12 and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
```

## Run

```sh
uv run tactile            # launch the trainer (lesson map)
uv run tactile practice path/to/file.py   # practice typing a code file
```

`python -m tactile` works as well. Inside the app: `enter` opens a unit,
`escape` leaves practice, `r` retries a unit from the results screen,
`p` opens the file picker, `l` changes layout, `q` quits.

## Tests

```sh
uv run pytest -q
```

## Progress

Progress is stored at `~/.tactile/progress.json` (schema versioned, written
atomically). Deleting the file resets all progress; a corrupt file is backed
up to `progress.json.bak` and the app starts fresh.
