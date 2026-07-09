"""Latin American Spanish (es-LA) keyboard layout data.

Physical positions verified against the Windows KBDLA layout (kbdlayout.info,
mirroring KBDLA.dll) for the invariants that matter for touch-typing: home
row (a s d f g h j k l ñ), the acute/diaeresis dead key right of P producing
á é í ó ú / ü, AltGr+Q for @, ¿/¡ on the number row, and </> left of Z.

One deliberate deviation from a first-draft assumption: on the real layout,
`{` and `}` are the UNSHIFTED base characters of the two keys right of Ñ
(shift gives `[` and `]`; AltGr on those same keys gives `^` and a
backtick) - not AltGr as originally guessed. Verified via kbdlayout.info
before writing this data. The design spec explicitly allows this kind of
simplification for symbol placement as long as home row/letters/ñ/accents/
digits are right, which they are.
"""

from __future__ import annotations

from tactile.layouts import Layout, add_dead_key_vowels, build_char_map

_ROWS: list[list[str]] = [
    list("|1234567890'¿"),
    list("qwertyuiop´+"),
    list("asdfghjklñ{}"),
    list("<zxcvbnm,.-"),
]

_FINGERS: list[list[str]] = [
    [
        "left pinky", "left pinky", "left ring", "left middle", "left index", "left index",
        "right index", "right index", "right middle", "right ring", "right pinky",
        "right pinky", "right pinky",
    ],
    [
        "left pinky", "left ring", "left middle", "left index", "left index",
        "right index", "right index", "right middle", "right ring", "right pinky",
        "right pinky", "right pinky",
    ],
    [
        "left pinky", "left ring", "left middle", "left index", "left index",
        "right index", "right index", "right middle", "right ring", "right pinky",
        "right pinky", "right pinky",
    ],
    [
        "left pinky", "left pinky", "left ring", "left middle", "left index", "left index",
        "right index", "right index", "right middle", "right ring", "right pinky",
    ],
]

_SHIFT_PAIRS: dict[str, str] = {
    "1": "!", "2": '"', "3": "#", "4": "$", "5": "%", "6": "&", "7": "/",
    "8": "(", "9": ")", "0": "=", "'": "?", "¿": "¡",
    "+": "*", "{": "[", "}": "]",
    ",": ";", ".": ":", "-": "_",
    "<": ">",
}

_ALTGR_PAIRS: dict[str, str] = {
    "q": "@",
    "+": "~",
    "{": "^",
    "}": "`",
}

KEY_ORDER_ES: list[tuple[str, str]] = [
    ("Fila base: F y J", "fj"), ("Fila base: D y K", "dk"), ("Fila base: S y L", "sl"),
    ("Fila base: A y Ñ", "añ"), ("Centro: G y H", "gh"), ("Fila superior: E e I", "ei"),
    ("Fila superior: R y U", "ru"), ("Fila superior: T e Y", "ty"), ("Fila superior: W y O", "wo"),
    ("Fila superior: Q y P", "qp"), ("Fila inferior: V y M", "vm"), ("Fila inferior: B y N", "bn"),
    ("Fila inferior: C y ,", "c,"), ("Fila inferior: X y .", "x."), ("Fila inferior: Z y -", "z-"),
    ("Mayúsculas (Shift)", "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"),
    ("Acentos y diéresis", "áéíóúü"), ("Puntuación", "'?!¿¡"), ("Números", "0123456789"),
    ("Símbolos", '"#$%&/()='), ("Símbolos de código I", "+*{}[]"),
    ("Símbolos de código II", "<>|~^@_"),
]

_char_map = build_char_map(_ROWS, _FINGERS, _SHIFT_PAIRS, _ALTGR_PAIRS)
add_dead_key_vowels(
    _char_map,
    {
        "á": ("a", "´ then a"),
        "é": ("e", "´ then e"),
        "í": ("i", "´ then i"),
        "ó": ("o", "´ then o"),
        "ú": ("u", "´ then u"),
        "ü": ("u", "¨ then u"),
    },
)

ES_LA = Layout(
    id="es_la",
    name="Español (Latinoamérica)",
    rows=_ROWS,
    char_map=_char_map,
    key_order=KEY_ORDER_ES,
)
