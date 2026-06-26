import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from kbdlayout import Model, load_model, render_svg


SVG_NS = {"svg": "http://www.w3.org/2000/svg"}
ROOT = Path(__file__).parents[1]
def test_render_svg_preserves_key_identity_and_outline(generated_models):
    model = load_model(generated_models["pc-105-iso"])
    root = ET.fromstring(render_svg(model, scale=10))

    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.find("svg:g[@id='keyboard-geometry']/svg:g[@id='keys']", SVG_NS) is not None
    enter = root.find(".//svg:g[@data-key-id='RTRN']", SVG_NS)
    assert enter is not None
    assert enter.attrib["data-kbd-keycode"] == "28"
    assert enter.find("svg:title", SVG_NS).text == "RTRN\nkbd_keycode: 28"
    assert enter.find("svg:polygon", SVG_NS) is not None
    assert root.find("svg:g[@id='factory-legends']", SVG_NS) is not None
    assert root.find("svg:g[@id='overlay-legends']", SVG_NS) is not None


def test_render_svg_writes_key_ids_in_factory_legends(generated_models):
    model = load_model(generated_models["pc-104-ansi"])
    root = ET.fromstring(render_svg(model))

    labels = root.findall("svg:g[@id='factory-legends']/svg:text", SVG_NS)
    assert len(labels) == len(model.keys)
    esc = next(label for label in labels if label.text == "ESC")
    assert esc.attrib["class"] == "key-id"
    assert esc.attrib["text-anchor"] == "end"
    assert esc.attrib["dominant-baseline"] == "hanging"
    assert float(esc.attrib["x"]) > model.key("ESC").x
    assert float(esc.attrib["y"]) < model.key("ESC").y + model.key("ESC").h / 2


def test_render_svg_uses_imported_key_colors(generated_models):
    model = load_model(generated_models["pc-104-ansi"])
    root = ET.fromstring(render_svg(model))

    esc = root.find(".//svg:g[@data-key-id='ESC']/svg:rect", SVG_NS)
    assert esc is not None
    assert esc.attrib["style"] == "--key-fill: #555"

    space = root.find(".//svg:g[@data-key-id='SPCE']/svg:rect", SVG_NS)
    assert space is not None
    assert space.attrib["style"] == "--key-fill: #f6f6f6"

    labels = root.findall("svg:g[@id='factory-legends']/svg:text", SVG_NS)
    esc_label = next(label for label in labels if label.text == "ESC")
    assert esc_label.attrib["style"] == "--key-id-fill: #eee"
    space_label = next(label for label in labels if label.text == "SPCE")
    assert space_label.attrib["style"] == "--key-id-fill: #555"


def test_render_svg_uses_imported_corner_radius(generated_models):
    model = load_model(generated_models["pc-104-ansi"])
    root = ET.fromstring(render_svg(model))

    esc = root.find(".//svg:g[@data-key-id='ESC']/svg:rect", SVG_NS)
    assert esc is not None
    assert esc.attrib["rx"] == "0.0555555555556"
    assert esc.attrib["ry"] == "0.0555555555556"


def test_render_svg_uses_geometry_bounds_as_frame(generated_models):
    model = load_model(generated_models["pc-104-ansi"])
    root = ET.fromstring(render_svg(model))

    frame = root.find("svg:g[@id='keyboard-geometry']/svg:g[@id='keyboard-decorations']/svg:rect", SVG_NS)
    assert frame is not None
    assert frame.attrib["class"] == "keyboard-frame"
    assert frame.attrib["x"] == "0"
    assert frame.attrib["y"] == "0"
    assert frame.attrib["width"] == "26.1111111111"
    assert frame.attrib["height"] == "10"


def test_render_svg_uses_outline_doodads():
    model = Model.from_data(
        {
            "version": 1,
            "id": "decorated",
            "unit": "u",
            "bounds": {"x": 0, "y": 0, "w": 4, "h": 2},
            "doodads": [
                {
                    "type": "outline",
                    "id": "Edges",
                    "x": 0,
                    "y": 0,
                    "w": 4,
                    "h": 2,
                    "corner_radius": 0.2,
                }
            ],
            "keys": [{"id": "KEY", "kbd_keycode": 1, "x": 1, "y": 0.5, "w": 1, "h": 1}],
        }
    )

    root = ET.fromstring(render_svg(model))
    frame = root.find("svg:g[@id='keyboard-geometry']/svg:g[@id='keyboard-decorations']/svg:rect", SVG_NS)
    assert frame is not None
    assert frame.attrib["id"] == "doodad-Edges"
    assert frame.attrib["rx"] == "0.2"
    assert frame.attrib["ry"] == "0.2"
    assert root.find(".//svg:g[@data-key-id='KEY']", SVG_NS) is not None


@pytest.mark.parametrize("option", ["--scale=0", "--padding=-1"])
def test_cli_rejects_invalid_render_options(option, generated_models):
    result = subprocess.run(
        [sys.executable, "src/kbd-layout.py", option, str(generated_models["pc-104-ansi"])],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "error:" in result.stderr


def test_cli_writes_svg(generated_models):
    result = subprocess.run(
        [sys.executable, "src/kbd-layout.py", str(generated_models["pc-104-ansi"])],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    root = ET.fromstring(result.stdout)
    assert len(root.findall(".//svg:g[@data-key-id]", SVG_NS)) == 104


def test_all_catalog_models_render(generated_models):
    for path in generated_models.values():
        model = load_model(path)
        root = ET.fromstring(render_svg(model))
        keys = root.findall(".//svg:g[@data-key-id]", SVG_NS)
        assert len(keys) == len(model.keys)


def test_renderer_applies_rotation_to_rectangular_keys():
    model = Model.from_data(
        {
            "version": 1,
            "id": "rotated",
            "unit": "u",
            "keys": [
                {
                    "id": "KEY",
                    "kbd_keycode": 1,
                    "x": 0,
                    "y": 0,
                    "w": 2,
                    "h": 1,
                    "rotation": {"angle": 90, "origin": [0, 0]},
                }
            ],
        }
    )

    root = ET.fromstring(render_svg(model))
    key = root.find(".//svg:g[@data-key-id='KEY']", SVG_NS)
    assert key is not None
    assert key.find("svg:rect", SVG_NS) is None
    assert key.find("svg:polygon", SVG_NS).attrib["points"] == "0,0 0,2 -1,2 -1,0"
