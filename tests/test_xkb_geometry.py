import json
from pathlib import Path

import pytest

from kbdlayout import load_model
from kbdlayout.importers import EVDEV_OFFSET, import_xkb_geometry
from kbdlayout.importers.xkb_geometry import XkbGeometryError


ROOT = Path(__file__).parents[1]
GEOMETRY = ROOT / "external" / "xkeyboard-config" / "geometry" / "pc"
KEYCODES = ROOT / "external" / "xkeyboard-config" / "keycodes" / "evdev"
@pytest.mark.parametrize(
    ("geometry", "model_id", "name", "key_count"),
    [
        ("pc104", "pc-104-ansi", "PC 104-key ANSI", 104),
        ("pc105", "pc-105-iso", "PC 105-key ISO", 105),
    ],
)
def test_catalog_models_are_imported_from_xkeyboard_config(geometry, model_id, name, key_count, generated_models):
    imported = import_xkb_geometry(GEOMETRY, KEYCODES, geometry, model_id=model_id, name=name, fallback_keycodes_paths=(ROOT / "external" / "xkeyboard-config" / "keycodes" / "xfree86",))

    assert imported == json.loads(generated_models[model_id].read_text())
    assert len(load_model(generated_models[model_id]).keys) == key_count
    assert imported["extensions"]["xkb"]["evdev_offset"] == EVDEV_OFFSET


def test_evdev_mapping_uses_the_documented_offset(generated_models):
    model = load_model(generated_models["pc-105-iso"])

    assert model.key("ESC").kbd_keycode == 1
    assert model.key("AE01").kbd_keycode == 2
    assert model.key("LSGT").kbd_keycode == 86
    assert model.key("MENU").kbd_keycode == 127
    assert model.key("RTRN").outline is not None


def test_importer_resolves_geometry_includes(tmp_path):
    (tmp_path / "base").write_text(
        '''xkb_geometry "common" {
            shape "NORM" { { [18,18] } };
            key.shape = "NORM";
            section "Base" { row { keys { <ESC> }; }; };
        };'''
    )
    (tmp_path / "child").write_text(
        '''xkb_geometry "child" {
            include "base(common)"
            section "Child" { row { keys { <AE01> }; }; };
        };'''
    )
    keycodes = tmp_path / "evdev"
    keycodes.write_text("<ESC> = 9;\n<AE01> = 10;\n")

    model = import_xkb_geometry(tmp_path / "child", keycodes, "child", model_id="child")

    assert [key["id"] for key in model["keys"]] == ["ESC", "AE01"]
    assert [group["id"] for group in model["groups"]] == ["base", "child"]


def test_importer_honors_negative_shape_origins(tmp_path):
    geometry = tmp_path / "geometry"
    geometry.write_text(
        '''xkb_geometry "negative" {
            shape "NORM" { { [18,18] } };
            shape "RTRN" { { [-14,19], [-14,37], [28,37], [28,0], [0,0], [0,19] } };
            key.shape = "NORM";
            key.gap = 1;
            section "Alpha" {
                row { keys { <AD11>, <AD12>, { <RTRN>, "RTRN" } }; };
            };
        };'''
    )
    keycodes = tmp_path / "evdev"
    keycodes.write_text("<AD11> = 35;\n<AD12> = 36;\n<RTRN> = 36;\n")

    model = import_xkb_geometry(geometry, keycodes, "negative", model_id="negative")
    enter = next(key for key in model["keys"] if key["id"] == "RTRN")

    assert enter["x"] == pytest.approx((1 + 18 + 1 + 18 + 1 - 14) / 18)
    assert enter["y"] == 0
    assert enter["w"] == pytest.approx(42 / 18)
    assert enter["h"] == pytest.approx(37 / 18)
    assert enter["outline"][0] == [0, pytest.approx(19 / 18)]


def test_importer_accepts_gap_before_shape_name(tmp_path):
    geometry = tmp_path / "geometry"
    geometry.write_text(
        '''xkb_geometry "gap_shape" {
            shape "NORM" { { [18,18] } };
            shape "WIDE" { { [42,18] } };
            key.shape = "NORM";
            section "Alpha" {
                row { keys { <AD11>, { <RTRN>, 1, "WIDE" } }; };
            };
        };'''
    )
    keycodes = tmp_path / "evdev"
    keycodes.write_text("<AD11> = 35;\n<RTRN> = 36;\n")

    model = import_xkb_geometry(geometry, keycodes, "gap_shape", model_id="gap_shape")
    enter = next(key for key in model["keys"] if key["id"] == "RTRN")

    assert enter["x"] == pytest.approx((18 + 1) / 18)
    assert enter["w"] == pytest.approx(42 / 18)


def test_importer_preserves_key_colors(tmp_path):
    geometry = tmp_path / "geometry"
    geometry.write_text(
        '''xkb_geometry "colors" {
            shape "NORM" { { [18,18] } };
            key.shape = "NORM";
            key.color = "grey20";
            section "Alpha" {
                row {
                    keys { <ESC>, { <SPCE>, color="white" } };
                };
            };
        };'''
    )
    keycodes = tmp_path / "evdev"
    keycodes.write_text("<ESC> = 9;\n<SPCE> = 65;\n")

    model = import_xkb_geometry(geometry, keycodes, "colors", model_id="colors")

    assert next(key for key in model["keys"] if key["id"] == "ESC")["color"] == "grey20"
    assert next(key for key in model["keys"] if key["id"] == "SPCE")["color"] == "white"


def test_importer_rejects_cyclic_geometry_includes(tmp_path):
    (tmp_path / "a").write_text('xkb_geometry "a" { include "b(b)" };')
    (tmp_path / "b").write_text('xkb_geometry "b" { include "a(a)" };')
    keycodes = tmp_path / "evdev"
    keycodes.write_text("")

    with pytest.raises(XkbGeometryError, match="cyclic geometry include"):
        import_xkb_geometry(tmp_path / "a", keycodes, "a", model_id="a")


def test_importer_uses_fallback_keycodes_and_keeps_non_kbd_codes(tmp_path, capsys):
    geometry = tmp_path / "geometry"
    geometry.write_text(
        '''xkb_geometry "vendor" {
            shape "NORM" { { [18,18] } };
            key.shape = "NORM";
            section "Vendor" { row { keys { <I1F>, <FN> }; }; };
        };'''
    )
    primary = tmp_path / "evdev"
    primary.write_text("<FN> = 472;\n")
    fallback = tmp_path / "xfree86"
    fallback.write_text("<I1F> = 159;\n")

    model = import_xkb_geometry(
        geometry,
        primary,
        "vendor",
        model_id="vendor",
        fallback_keycodes_paths=(fallback,),
    )

    assert [(key["id"], key["kbd_keycode"]) for key in model["keys"]] == [("I1F", 151), ("FN", 464)]
    assert "FN: kernel keycode 464 is outside NR_KEYS=256" in capsys.readouterr().err
