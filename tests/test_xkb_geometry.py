import json
from pathlib import Path

import pytest

from kbdlayout import load_model
from kbdlayout.importers import EVDEV_OFFSET, import_xkb_geometry


ROOT = Path(__file__).parents[1]
GEOMETRY = ROOT / "external" / "xkeyboard-config" / "geometry" / "pc"
KEYCODES = ROOT / "external" / "xkeyboard-config" / "keycodes" / "evdev"
FIXTURES = ROOT / "models" / "fixtures"


@pytest.mark.parametrize(
    ("geometry", "model_id", "name", "filename", "key_count"),
    [
        ("pc104", "pc-104-ansi", "PC 104-key ANSI", "pc-104-ansi.json", 104),
        ("pc105", "pc-105-iso", "PC 105-key ISO", "pc-105-iso.json", 105),
    ],
)
def test_pc_fixtures_are_imported_from_xkeyboard_config(geometry, model_id, name, filename, key_count):
    imported = import_xkb_geometry(GEOMETRY, KEYCODES, geometry, model_id=model_id, name=name)

    assert imported == json.loads((FIXTURES / filename).read_text())
    assert len(load_model(FIXTURES / filename).keys) == key_count
    assert imported["extensions"]["xkb"]["evdev_offset"] == EVDEV_OFFSET


def test_evdev_mapping_uses_the_documented_offset():
    model = load_model(FIXTURES / "pc-105-iso.json")

    assert model.key("ESC").linux_keycode == 1
    assert model.key("AE01").linux_keycode == 2
    assert model.key("LSGT").linux_keycode == 86
    assert model.key("MENU").linux_keycode == 127
    assert model.key("RTRN").outline is not None
