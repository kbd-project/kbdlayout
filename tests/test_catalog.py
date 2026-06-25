import json
import subprocess
import sys
from pathlib import Path

import pytest

from kbdlayout.catalog import catalog_data, load_catalog


ROOT = Path(__file__).parents[1]


def test_load_catalog_entries():
    entries = load_catalog(ROOT / "models" / "catalog.tsv")

    assert entries[0].model_id == "pc-104-ansi"
    assert entries[0].json_path == "pc-104-ansi.json"
    assert entries[0].svg_path == "pc-104-ansi.svg"


def test_catalog_data_contains_static_model_paths():
    data = catalog_data(load_catalog(ROOT / "models" / "catalog.tsv"))

    assert data["version"] == 1
    assert data["models"][0] == {
        "id": "pc-104-ansi",
        "name": "PC 104-key ANSI",
        "group": "PC",
        "geometry_file": "pc",
        "geometry": "pc104",
        "json": "pc-104-ansi.json",
        "svg": "pc-104-ansi.svg",
    }


def test_catalog_cli_writes_json(tmp_path):
    output = tmp_path / "catalog.json"

    subprocess.run(
        [sys.executable, "src/generate-model-catalog.py", "models/catalog.tsv", str(output)],
        cwd=ROOT,
        check=True,
    )

    data = json.loads(output.read_text())
    assert data["models"][0]["id"] == "pc-104-ansi"


def test_catalog_rejects_duplicate_model_ids(tmp_path):
    catalog = tmp_path / "catalog.tsv"
    catalog.write_text("pc\tpc104\tpc-104-ansi\tPC 104\npc\tpc105\tpc-104-ansi\tPC 105\n")

    with pytest.raises(ValueError, match="duplicate model id"):
        load_catalog(catalog)
