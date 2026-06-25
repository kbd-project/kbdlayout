"""Model catalog loading and JSON export."""

from __future__ import annotations

from dataclasses import dataclass
import csv
import json
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class CatalogEntry:
    """One generated physical model entry."""

    geometry_file: str
    geometry: str
    model_id: str
    name: str

    @property
    def json_path(self) -> str:
        """Return the model JSON path relative to the generated catalog."""
        return f"{self.model_id}.json"

    @property
    def svg_path(self) -> str:
        """Return the model SVG path relative to the generated catalog."""
        return f"{self.model_id}.svg"

    def to_json(self) -> dict[str, str]:
        """Return the public JSON representation for this entry."""
        return {
            "id": self.model_id,
            "name": self.name,
            "geometry_file": self.geometry_file,
            "geometry": self.geometry,
            "json": self.json_path,
            "svg": self.svg_path,
        }


def load_catalog(path: str | Path) -> tuple[CatalogEntry, ...]:
    """Load model catalog entries from a tab-separated catalog file."""
    entries: list[CatalogEntry] = []
    catalog_path = Path(path)
    with catalog_path.open(newline="", encoding="utf-8") as file:
        for line_number, row in enumerate(csv.reader(file, delimiter="\t"), start=1):
            if not row or row[0].startswith("#"):
                continue
            if len(row) != 4:
                raise ValueError(f"{catalog_path}:{line_number}: expected 4 tab-separated fields")
            geometry_file, geometry, model_id, name = row
            entries.append(
                CatalogEntry(
                    geometry_file=_field(geometry_file, catalog_path, line_number, "geometry-file"),
                    geometry=_field(geometry, catalog_path, line_number, "geometry"),
                    model_id=_field(model_id, catalog_path, line_number, "model-id"),
                    name=_field(name, catalog_path, line_number, "name"),
                )
            )

    _unique((entry.model_id for entry in entries), "model id")
    return tuple(entries)


def catalog_data(entries: Iterable[CatalogEntry]) -> dict[str, Any]:
    """Return the public generated catalog document."""
    return {
        "version": 1,
        "models": [entry.to_json() for entry in entries],
    }


def write_catalog_json(catalog_path: str | Path, output_path: str | Path) -> None:
    """Generate the public JSON catalog from the source TSV catalog."""
    data = catalog_data(load_catalog(catalog_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"{json.dumps(data, indent=2)}\n", encoding="utf-8")


def _field(value: str, catalog_path: Path, line_number: int, name: str) -> str:
    if not value:
        raise ValueError(f"{catalog_path}:{line_number}: {name} must not be empty")
    return value


def _unique(values: Iterable[str], description: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"duplicate {description}: {value}")
        seen.add(value)
