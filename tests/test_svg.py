import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from kbdlayout import Model, load_model, render_svg


SVG_NS = {"svg": "http://www.w3.org/2000/svg"}
ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "models" / "fixtures"


def test_render_svg_preserves_key_identity_and_outline():
    model = load_model(FIXTURES / "pc-105-iso.json")
    root = ET.fromstring(render_svg(model, scale=10))

    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.find("svg:g[@id='keyboard-geometry']/svg:g[@id='keys']", SVG_NS) is not None
    enter = root.find(".//svg:g[@data-key-id='RTRN']", SVG_NS)
    assert enter is not None
    assert enter.attrib["data-linux-keycode"] == "28"
    assert enter.find("svg:polygon", SVG_NS) is not None
    assert root.find("svg:g[@id='factory-legends']", SVG_NS) is not None
    assert root.find("svg:g[@id='overlay-legends']", SVG_NS) is not None


@pytest.mark.parametrize("option", ["--scale=0", "--padding=-1"])
def test_cli_rejects_invalid_render_options(option):
    result = subprocess.run(
        [sys.executable, "src/kbd-layout.py", option, str(FIXTURES / "pc-104-ansi.json")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "error:" in result.stderr


def test_cli_writes_svg():
    result = subprocess.run(
        [sys.executable, "src/kbd-layout.py", str(FIXTURES / "pc-104-ansi.json")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    root = ET.fromstring(result.stdout)
    assert len(root.findall(".//svg:g[@data-key-id]", SVG_NS)) == 104


def test_renderer_applies_rotation_to_rectangular_keys():
    model = Model.from_data(
        {
            "version": 1,
            "id": "rotated",
            "unit": "u",
            "keys": [
                {
                    "id": "KEY",
                    "linux_keycode": 1,
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
