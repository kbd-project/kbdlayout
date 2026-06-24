import json
from pathlib import Path

import pytest

from kbdlayout import Model, ModelError, load_model


FIXTURES = Path(__file__).parents[1] / "models" / "fixtures"


@pytest.mark.parametrize("filename", ["pc-104-ansi.json", "pc-105-iso.json"])
def test_load_fixtures(filename):
    model = load_model(FIXTURES / filename)

    assert model.key("ESC").linux_keycode == 1
    assert model.keycode(1).id == "ESC"
    assert model.bounds().w > 0
    assert model.bounds().h > 0


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda data: data["keys"].append(data["keys"][0].copy()), "duplicate key ID"),
        (lambda data: data["keys"][0].update({"outline": [[0, 0], [2, 0], [0, 1]]}), "outside the key bounds"),
        (lambda data: data["groups"][0]["key_ids"].append("MISSING"), "references unknown keys"),
    ],
)
def test_reject_invalid_models(change, message):
    data = json.loads((FIXTURES / "pc-104-ansi.json").read_text())
    change(data)

    with pytest.raises(ModelError, match=message):
        Model.from_data(data)


def test_rotated_key_bounds():
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

    bounds = model.bounds()
    assert bounds.x == pytest.approx(-1)
    assert bounds.y == pytest.approx(0)
    assert bounds.w == pytest.approx(1)
    assert bounds.h == pytest.approx(2)
