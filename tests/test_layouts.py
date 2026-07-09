"""Tests for keyboard layout data (en_us, es_la)."""

from __future__ import annotations

import pytest

from touchtype.layouts import LAYOUTS


def test_layouts_has_both_ids():
    assert set(LAYOUTS) == {"en_us", "es_la"}


def test_layout_names():
    assert LAYOUTS["en_us"].name == "English (US)"
    assert LAYOUTS["es_la"].name == "Español (Latinoamérica)"


def test_en_us_f_key_is_left_index_on_home_row():
    info = LAYOUTS["en_us"].char_map["f"]
    assert info.finger == "left index"
    assert info.row == 2


def test_en_us_home_row_positions():
    char_map = LAYOUTS["en_us"].char_map
    assert char_map["a"].row == 2 and char_map["a"].col == 0
    assert char_map["f"].col == 3
    assert char_map["j"].col == 6
    assert char_map["j"].finger == "right index"


def test_es_la_home_row_is_a_s_d_f_g_h_j_k_l_ene():
    assert LAYOUTS["es_la"].rows[2][:10] == [
        "a", "s", "d", "f", "g", "h", "j", "k", "l", "ñ",
    ]


def test_en_us_brace_is_shift_modifier():
    assert LAYOUTS["en_us"].char_map["{"].modifier == "shift"


def test_es_la_at_sign_is_altgr_modifier():
    # @ is the canonical AltGr character on the Latin American layout (AltGr+Q).
    assert LAYOUTS["es_la"].char_map["@"].modifier == "altgr"


def test_es_la_accented_vowel_is_dead_key_modifier():
    info = LAYOUTS["es_la"].char_map["á"]
    assert info.modifier == "dead"
    assert info.hint  # non-empty hint describing the dead-key combo


@pytest.mark.parametrize("layout_id", ["en_us", "es_la"])
def test_every_key_order_char_is_typable(layout_id: str):
    layout = LAYOUTS[layout_id]
    for _title, chars in layout.key_order:
        for char in chars:
            assert layout.typable(char), f"{layout_id}: {char!r} not typable"


@pytest.mark.parametrize("layout_id", ["en_us", "es_la"])
def test_no_char_repeats_across_key_order_entries(layout_id: str):
    layout = LAYOUTS[layout_id]
    seen: set[str] = set()
    for _title, chars in layout.key_order:
        for char in chars:
            assert char not in seen, f"{layout_id}: {char!r} appears in two key_order entries"
            seen.add(char)


def test_uppercase_letters_resolve_to_base_key_with_shift_modifier():
    en = LAYOUTS["en_us"].char_map
    assert en["A"].row == en["a"].row
    assert en["A"].col == en["a"].col
    assert en["A"].finger == en["a"].finger
    assert en["A"].modifier == "shift"

    es = LAYOUTS["es_la"].char_map
    assert es["Ñ"].row == es["ñ"].row
    assert es["Ñ"].col == es["ñ"].col
    assert es["Ñ"].finger == es["ñ"].finger
    assert es["Ñ"].modifier == "shift"


def test_layout_typable_accepts_space_and_newline():
    for layout in LAYOUTS.values():
        assert layout.typable(" ")
        assert layout.typable("\n")


def test_layout_typable_rejects_unknown_char():
    for layout in LAYOUTS.values():
        assert not layout.typable("\t")
