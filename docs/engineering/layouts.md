# Layouts

The `layouts/` package holds keyboard layout **data**, not logic. Each layout
describes physical key positions, the finger for each key, and the modifier
needed to produce each character. The curriculum generator and the code
loader both ask `Layout.typable(char)` to decide what a learner can type.

## The data model

```python
Modifier = Literal["none", "shift", "altgr", "dead"]

@dataclass(frozen=True)
class KeyInfo:
    row: int          # 0=number row, 1=top, 2=home, 3=bottom
    col: int
    finger: str       # "left pinky" | "left ring" | ... | "thumb"
    modifier: Modifier
    hint: str = ""    # extra hint for dead-key chars, e.g. "´ then a"

@dataclass(frozen=True)
class Layout:
    id: str                          # "en_us" | "es_la"
    name: str                        # "English (US)" | "Español (Latinoamérica)"
    rows: list[list[str]]            # base cap per physical key, one list per row
    char_map: dict[str, KeyInfo]     # char -> where it lives and how to produce it
    key_order: list[tuple[str, str]] # (unit title, new chars) — the curriculum spine

    def typable(self, char: str) -> bool:
        return char in self.char_map or char in (" ", "\n")
```

`LAYOUTS: dict[str, Layout]` at the bottom of `__init__.py` exposes every
layout by id:

```python
LAYOUTS = {"en_us": EN_US, "es_la": ES_LA}
```

## `build_char_map`

Builds a `char_map` from parallel row/finger data plus shift/AltGr pairs.
For every base key it records a `modifier="none"` entry; for every
alphabetic base char it also records the uppercase form with
`modifier="shift"`; and it adds any `shift_pairs` / `altgr_pairs`:

```python
for row_index, row_chars in enumerate(rows):
    for col_index, char in enumerate(row_chars):
        char_map[char] = KeyInfo(row=row_index, col=col_index, finger=finger, modifier="none")
        if char.isalpha():
            char_map[char.upper()] = KeyInfo(..., modifier="shift")
        if char in shift_pairs:
            char_map[shift_pairs[char]] = KeyInfo(..., modifier="shift")
        if char in altgr_pairs:
            char_map[altgr_pairs[char]] = KeyInfo(..., modifier="altgr")
```

## `add_dead_key_vowels`

Dead-key composed characters (e.g. `á`) are positioned at the **vowel's**
key, with `modifier="dead"` and a human-readable `hint`:

```python
def add_dead_key_vowels(char_map, composed):
    for composed_char, (base_char, hint) in composed.items():
        base_info = char_map[base_char]
        char_map[composed_char] = KeyInfo(
            row=base_info.row, col=base_info.col,
            finger=base_info.finger, modifier="dead", hint=hint,
        )
```

So `á` lives on the `a` key and shows the hint `"´ then a"`.

## en_us — English (US) QWERTY

- Four physical rows: `` `1234567890-= ``, `qwertyuiop[]\`,
  `asdfghjkl;'`, `zxcvbnm,./`.
- Finger assignments follow the standard touch-typing map (left pinky →
  right pinky, with the index fingers covering two columns each).
- `_SHIFT_PAIRS` maps each base char to its shifted symbol
  (`` ` ``→`~`, `1`→`!`, …, `/`→`?`).
- **No AltGr pairs** — en_us does not use AltGr.
- `KEY_ORDER_EN` has 21 entries, introducing keys home-row outward:
  `fj`, `dk`, `sl`, `a;`, `gh`, then the top row, the bottom row, capitals,
  punctuation, numbers, symbols, and two code-symbol groups.

## es_la — Español (Latinoamérica)

The es_la data is **verified against the Windows KBDLA layout**
(kbdlayout.info, mirroring `KBDLA.dll`) for the invariants that matter for
touch-typing. The module docstring records the verification and one
deliberate deviation.

### Key facts honoured

- **Home row** is `a s d f g h j k l ñ` (ñ is a home-row key).
- The `´` key (top row, right of `p`) is a **dead key** producing
  `á é í ó ú`; its shift `¨` produces `ü`. These use `modifier="dead"` with
  hints like `"´ then a"` and `"¨ then u"`.
- **AltGr pairs**: `AltGr+Q` = `@`, `AltGr++` = `~`, `AltGr+{` = `^`,
  `AltGr+}` = `` ` ``.
- `¿` and `¡` are on the number-row area; `<`/`>` on the key left of `z`.
- `KEY_ORDER_ES` has 22 entries — the same outward-from-home-row shape as
  en_us, plus a dedicated `("Acentos y diéresis", "áéíóúü")` unit.

### The `{`/`}` deviation

On a first-draft assumption, `{` and `}` were guessed to be AltGr
combinations. The real KBDLA layout has them as the **unshifted base**
characters of the two keys right of `ñ` — shift on those keys gives `[` and
`]`, and AltGr gives `^` and a backtick. The es_la module was corrected to
match KBDLA before the layout tests were written, and the deviation is
documented in the module docstring:

> on the real layout, `{` and `}` are the UNSHIFTED base characters of the
> two keys right of Ñ (shift gives `[` and `]`; AltGr on those same keys
> gives `^` and a backtick) — not AltGr as originally guessed.

The design spec explicitly allows this kind of simplification for symbol
placement as long as home row, letters, ñ, accents, and digits are right —
which they are.

### Spanish unit titles

`KEY_ORDER_ES` unit titles are in Spanish (`"Fila base: F y J"`,
`"Mayúsculas (Shift)"`, …) because they are **curriculum content** for
Spanish-layout learners, not UI chrome. The UI chrome stays English by
decision.

## How layouts are used

| Consumer | How |
|----------|-----|
| `build_curriculum` | walks `layout.key_order`; filters wordlist words by `layout.typable`; finalizes exercises to typable chars |
| `load_code_exercises` | keeps only chars where `layout.typable(char)`; collects the rest into a "skipped untypable" notice |
| `KeyboardWidget` | renders `layout.rows`; looks up `layout.char_map[char]` to highlight the next key and show finger + modifier |
| `ProgressStore` | keyed by `layout.id`; each layout gets its own lessons and key-error heatmap |

## Adding a new layout

1. Create `src/tactile/layouts/<id>.py` with `_ROWS`, `_FINGERS`,
   `_SHIFT_PAIRS`, an optional `_ALTGR_PAIRS`, and a `KEY_ORDER_<X>`.
2. Build the `char_map` with `build_char_map` (and `add_dead_key_vowels`
   if the layout has dead keys).
3. Construct the `Layout` and export it.
4. Register it in `LAYOUTS` in `layouts/__init__.py`.
5. Add a wordlist under `src/tactile/wordlists/<id>.txt` and an entry in
   `_WORDLIST_FILES` in `curriculum.py`.
6. Cover it in `tests/test_layouts.py` (home row, modifiers, every
   `key_order` char is `typable`, no char repeats across entries).

See [development.md](development.md#adding-a-new-layout-or-wordlist) for the
full walkthrough.
