"""English (US) QWERTY keyboard layout data."""

from __future__ import annotations

from touchtype.layouts import Layout, build_char_map

_ROWS: list[list[str]] = [
    list("`1234567890-="),
    list("qwertyuiop[]\\"),
    list("asdfghjkl;'"),
    list("zxcvbnm,./"),
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
        "right pinky", "right pinky", "right pinky",
    ],
    [
        "left pinky", "left ring", "left middle", "left index", "left index",
        "right index", "right index", "right middle", "right ring", "right pinky",
        "right pinky",
    ],
    [
        "left pinky", "left ring", "left middle", "left index", "left index",
        "right index", "right index", "right middle", "right ring", "right pinky",
    ],
]

_SHIFT_PAIRS: dict[str, str] = {
    "`": "~", "1": "!", "2": "@", "3": "#", "4": "$", "5": "%", "6": "^",
    "7": "&", "8": "*", "9": "(", "0": ")", "-": "_", "=": "+",
    "[": "{", "]": "}", "\\": "|",
    ";": ":", "'": '"',
    ",": "<", ".": ">", "/": "?",
}

KEY_ORDER_EN: list[tuple[str, str]] = [
    ("Home row: F & J", "fj"), ("Home row: D & K", "dk"), ("Home row: S & L", "sl"),
    ("Home row: A & ;", "a;"), ("Center: G & H", "gh"), ("Top row: E & I", "ei"),
    ("Top row: R & U", "ru"), ("Top row: T & Y", "ty"), ("Top row: W & O", "wo"),
    ("Top row: Q & P", "qp"), ("Bottom: V & M", "vm"), ("Bottom: B & N", "bn"),
    ("Bottom: C & ,", "c,"), ("Bottom: X & .", "x."), ("Bottom: Z & /", "z/"),
    ("Capitals (Shift)", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    ("Punctuation", "'\"!?"), ("Numbers", "0123456789"),
    ("Symbols", "@#$%^&*()"), ("Code symbols I", "-_=+[]{}"),
    ("Code symbols II", "<>:\\|~`"),
]

EN_US = Layout(
    id="en_us",
    name="English (US)",
    rows=_ROWS,
    char_map=build_char_map(_ROWS, _FINGERS, _SHIFT_PAIRS),
    key_order=KEY_ORDER_EN,
)
