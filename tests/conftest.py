import csv
import json
from pathlib import Path

import pytest

from kbdlayout.importers import import_xkb_geometry


ROOT = Path(__file__).parents[1]
CATALOG = ROOT / "models" / "catalog.tsv"
GEOMETRY_DIR = ROOT / "external" / "xkeyboard-config" / "geometry"
KEYCODES = ROOT / "external" / "xkeyboard-config" / "keycodes"


def model_catalog():
    with CATALOG.open(newline="") as file:
        for row in csv.reader(file, delimiter="\t"):
            if not row or row[0].startswith("#"):
                continue
            geometry_file, geometry, model_id, name = row
            yield geometry_file, geometry, model_id, name


@pytest.fixture(scope="session")
def generated_models(tmp_path_factory):
    output = tmp_path_factory.mktemp("models")
    paths = {}
    for geometry_file, geometry, model_id, name in model_catalog():
        data = import_xkb_geometry(
            GEOMETRY_DIR / geometry_file,
            KEYCODES / "evdev",
            geometry,
            model_id=model_id,
            name=name,
            fallback_keycodes_paths=(KEYCODES / "xfree86",),
        )
        path = output / f"{model_id}.json"
        path.write_text(f"{json.dumps(data, indent=2)}\n")
        paths[model_id] = path
    return paths
