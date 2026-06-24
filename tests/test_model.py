import json
from pathlib import Path

import pytest

from kbdlayout import Model, ModelError, load_model


@pytest.mark.parametrize("model_id", ["pc-104-ansi", "pc-105-iso"])
def test_load_fixtures(model_id, generated_models):
    model = load_model(generated_models[model_id])

    assert model.key("ESC").kbd_keycode == 1
    assert model.keycode(1).id == "ESC"
    assert model.bounds().w > 0
    assert model.bounds().h > 0


def test_all_catalog_models_validate(generated_models):
    for path in generated_models.values():
        assert load_model(path).keys


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda data: data["keys"].append(data["keys"][0].copy()), "duplicate key ID"),
        (lambda data: data["keys"][0].update({"outline": [[0, 0], [2, 0], [0, 1]]}), "outside the key bounds"),
        (lambda data: data["groups"][0]["key_ids"].append("MISSING"), "references unknown keys"),
    ],
)
def test_reject_invalid_models(change, message, generated_models):
    data = json.loads(generated_models["pc-104-ansi"].read_text())
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

    bounds = model.bounds()
    assert bounds.x == pytest.approx(-1)
    assert bounds.y == pytest.approx(0)
    assert bounds.w == pytest.approx(1)
    assert bounds.h == pytest.approx(2)
