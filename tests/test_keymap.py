import json
import subprocess
import sys
from pathlib import Path

import pytest

from kbdlayout.keymap import discover_keymaps, keymap_catalog_data, keymap_data, parse_keymap_dump


ROOT = Path(__file__).parents[1]
LOADKEYS = ROOT / "external" / "kbd" / "src" / "loadkeys"
KEYMAPS_ROOT = ROOT / "external" / "kbd" / "data" / "keymaps"


def test_parse_keymap_dump_expands_header_and_keycodes():
    dump = """\
keymaps 0-1,4
keycode   1 = Escape Escape Escape
keycode  16 = +q +Q Control_q
"""

    parsed = parse_keymap_dump(dump)

    assert parsed.keymaps == (0, 1, 4)
    assert parsed.keys[1] == ("Escape", "Escape", "Escape")
    assert parsed.keys[16] == ("+q", "+Q", "Control_q")


def test_keymap_data_pairs_symbolic_and_numeric_values():
    symbolic = parse_keymap_dump(
        """\
keymaps 0-1
keycode  16 = +q +Q
"""
    )
    numeric = parse_keymap_dump(
        """\
keymaps 0-1
keycode  16 = +0x0b71 +0x0b51
"""
    )

    data = keymap_data(symbolic, numeric, keymap_id="i386/qwerty/us", source="i386/qwerty/us.map")

    assert data["version"] == 1
    assert data["id"] == "i386/qwerty/us"
    assert data["keymaps"] == [0, 1]
    assert data["keys"] == [
        {
            "kbd_keycode": 16,
            "entries": [
                {
                    "keymap": 0,
                    "symbol": "+q",
                    "numeric": "+0x0b71",
                    "numeric_value": 2929,
                    "has_plus_prefix": True,
                },
                {
                    "keymap": 1,
                    "symbol": "+Q",
                    "numeric": "+0x0b51",
                    "numeric_value": 2897,
                    "has_plus_prefix": True,
                },
            ],
        }
    ]


def test_keymap_data_rejects_mismatched_dumps():
    symbolic = parse_keymap_dump("keymaps 0\nkeycode  16 = +q\n")
    numeric = parse_keymap_dump("keymaps 1\nkeycode  16 = +0x0b71\n")

    with pytest.raises(ValueError, match="keymap headers differ"):
        keymap_data(symbolic, numeric, keymap_id="bad", source="bad.map")


def test_cli_imports_one_kbd_keymap(tmp_path):
    output = tmp_path / "us.json"

    subprocess.run(
        [
            sys.executable,
            "src/import-kbd-keymap.py",
            "external/kbd/data/keymaps/i386/qwerty/us.map",
            str(output),
            "--loadkeys",
            str(LOADKEYS),
            "--keymaps-root",
            str(KEYMAPS_ROOT),
        ],
        cwd=ROOT,
        check=True,
    )

    data = json.loads(output.read_text())
    key_q = next(key for key in data["keys"] if key["kbd_keycode"] == 16)
    assert data["id"] == "i386/qwerty/us"
    assert data["source"] == "i386/qwerty/us.map"
    assert data["keymaps"] == [0, 1, 2, 4, 5, 6, 8, 9, 12]
    assert key_q["entries"][0]["symbol"] == "+q"
    assert key_q["entries"][0]["numeric"] == "+0x0b71"
    assert key_q["entries"][0]["numeric_value"] == 2929


def test_discover_keymaps_skips_include_directories(tmp_path):
    (tmp_path / "qwerty").mkdir()
    (tmp_path / "include").mkdir()
    (tmp_path / "qwerty" / "us.map").write_text("")
    (tmp_path / "include" / "linux.map").write_text("")

    assert discover_keymaps(tmp_path) == (tmp_path / "qwerty" / "us.map",)


def test_keymap_catalog_data_contains_static_paths():
    data = keymap_catalog_data(
        [
            {
                "id": "i386/qwerty/us",
                "name": "i386/qwerty/us",
                "group": "qwerty",
                "source": "i386/qwerty/us.map",
                "json": "i386/qwerty/us.json",
            }
        ]
    )

    assert data == {
        "version": 1,
        "keymaps": [
            {
                "id": "i386/qwerty/us",
                "name": "i386/qwerty/us",
                "group": "qwerty",
                "source": "i386/qwerty/us.map",
                "json": "i386/qwerty/us.json",
            }
        ],
    }
