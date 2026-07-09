"""Keyboard layout data: physical key positions, fingers, and modifiers.

Pure data module - no I/O, no Textual dependency. `LAYOUTS` exposes every
supported layout by id; `Layout.typable()` tells the curriculum generator
and code-practice loader whether a character can be produced on a layout.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Modifier = Literal["none", "shift", "altgr", "dead"]


@dataclass(frozen=True)
class KeyInfo:
    row: int  # 0=number row, 1=top, 2=home, 3=bottom, 4=space row
    col: int
    finger: str
    modifier: Modifier
    hint: str = ""


@dataclass(frozen=True)
class Layout:
    id: str
    name: str
    rows: list[list[str]]
    char_map: dict[str, KeyInfo]
    key_order: list[tuple[str, str]]

    def typable(self, char: str) -> bool:
        return char in self.char_map or char in (" ", "\n")


def build_char_map(
    rows: list[list[str]],
    fingers: list[list[str]],
    shift_pairs: dict[str, str],
    altgr_pairs: dict[str, str] | None = None,
) -> dict[str, KeyInfo]:
    """Build a char_map from parallel row/finger data plus shift/altgr pairs.

    `rows` holds the unshifted base character of every key, one list per
    physical row; `fingers` mirrors that shape with the finger name for each
    key. Every alphabetic base char automatically gets an uppercase
    modifier="shift" entry at the same position.
    """
    char_map: dict[str, KeyInfo] = {}
    altgr_pairs = altgr_pairs or {}
    for row_index, row_chars in enumerate(rows):
        row_fingers = fingers[row_index]
        for col_index, char in enumerate(row_chars):
            finger = row_fingers[col_index]
            char_map[char] = KeyInfo(row=row_index, col=col_index, finger=finger, modifier="none")
            if char.isalpha():
                char_map[char.upper()] = KeyInfo(
                    row=row_index, col=col_index, finger=finger, modifier="shift"
                )
            if char in shift_pairs:
                char_map[shift_pairs[char]] = KeyInfo(
                    row=row_index, col=col_index, finger=finger, modifier="shift"
                )
            if char in altgr_pairs:
                char_map[altgr_pairs[char]] = KeyInfo(
                    row=row_index, col=col_index, finger=finger, modifier="altgr"
                )
    return char_map


def add_dead_key_vowels(
    char_map: dict[str, KeyInfo], composed: dict[str, tuple[str, str]]
) -> None:
    """Add dead-key composed chars (e.g. 'á'), positioned at the vowel's key.

    `composed` maps composed char -> (vowel_char, hint), e.g.
    `{"á": ("a", "´ then a")}`. The vowel's key must already be in char_map.
    """
    for composed_char, (base_char, hint) in composed.items():
        base_info = char_map[base_char]
        char_map[composed_char] = KeyInfo(
            row=base_info.row,
            col=base_info.col,
            finger=base_info.finger,
            modifier="dead",
            hint=hint,
        )


from touchtype.layouts.en_us import EN_US  # noqa: E402
from touchtype.layouts.es_la import ES_LA  # noqa: E402

LAYOUTS: dict[str, Layout] = {"en_us": EN_US, "es_la": ES_LA}
